"""
This module contains common model objects that are used to describe the data types used in the
pulp_docker plugins.
"""
import base64
import hashlib
import json
from gettext import gettext as _

import mongoengine
import os
from pulp.server.db import model as pulp_models, querysets

from pulp_docker.common import constants, error_codes
from pulp.server.exceptions import PulpCodedValidationException


MANIFEST_LIST_REQUIRED_FIELDS = ['manifests', 'mediaType', 'schemaVersion']
IMAGE_MANIFEST_REQUIRED_FIELDS = ['mediaType', 'digest', 'platform']
IMAGE_MANIFEST_REQUIRED_PLATFORM_SUBFIELDS = ['os', 'architecture']


class Blob(pulp_models.FileContentUnit):
    """
    This class is used to represent Docker v2 blobs.
    """
    digest = mongoengine.StringField(required=True)

    # For backward compatibility
    _ns = mongoengine.StringField(default='units_{type_id}'.format(type_id=constants.BLOB_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True, default=constants.BLOB_TYPE_ID)

    unit_key_fields = ('digest',)

    meta = {'collection': 'units_{type_id}'.format(type_id=constants.BLOB_TYPE_ID),
            'indexes': [],
            'allow_inheritance': False}

    def get_symlink_name(self):
        """
        Provides the name that should be used when creating a symlink.
        :return: file name as it appears in a published repository
        :rtype: str
        """
        return '/'.join(('blobs', self.digest))


class Image(pulp_models.FileContentUnit):
    """
    This class is used to represent Docker v1 images.
    """
    image_id = mongoengine.StringField(required=True)
    parent_id = mongoengine.StringField()
    size = mongoengine.IntField()

    # For backward compatibility
    _ns = mongoengine.StringField(default='units_{type_id}'.format(type_id=constants.IMAGE_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True, default=constants.IMAGE_TYPE_ID)

    unit_key_fields = ('image_id',)

    meta = {'collection': 'units_{type_id}'.format(type_id=constants.IMAGE_TYPE_ID),
            'indexes': [],
            'allow_inheritance': False}

    def list_files(self):
        """
        List absolute paths to files associated with this unit.

        :return: A list of absolute file paths.
        :rtype: list
        """
        names = ('ancestry', 'json', 'layer')
        return [os.path.join(self.storage_path, n) for n in names]

    def get_symlink_name(self):
        """
        Provides the name that should be used when creating a symlink.
        :return: file name as it appears in a published repository
        :rtype: str
        """
        return self.image_id


class FSLayer(mongoengine.EmbeddedDocument):
    """
    This EmbeddedDocument is used in the Manifest.fs_layers field. It references a Blob Document.
    """
    # This will be the digest of a Blob document.
    blob_sum = mongoengine.StringField(required=True)
    layer_type = mongoengine.StringField()


class UnitMixin(object):

    meta = {
        'abstract': True,
    }

    @staticmethod
    def calculate_digest(manifest, algorithm='sha256'):
        """
        Calculate the requested digest of the Manifest, given in JSON.

        :param manifest:  The raw JSON representation of the Manifest.
        :type  manifest:  basestring
        :param algorithm: The digest algorithm to use. Defaults to sha256. Must be one of the
                          algorithms included with hashlib.
        :type  algorithm: basestring
        :return:          The digest of the given Manifest
        :rtype:           basestring
        """
        decoded_manifest = json.loads(manifest, encoding='utf-8')
        if 'signatures' in decoded_manifest:
            # This manifest contains signatures. Unfortunately, the Docker manifest digest
            # is calculated on the unsigned version of the Manifest so we need to remove the
            # signatures. To do this, we will look at the 'protected' key within the first
            # signature. This key indexes a (malformed) base64 encoded JSON dictionary that
            # tells us how many bytes of the manifest we need to keep before the signature
            # appears in the original JSON and what the original ending to the manifest was after
            # the signature block. We will strip out the bytes after this cutoff point, add back the
            # original ending, and then calculate the sha256 sum of the transformed JSON to get the
            # digest.
            protected = decoded_manifest['signatures'][0]['protected']
            # Add back the missing padding to the protected block so that it is valid base64.
            protected = UnitMixin._pad_unpadded_b64(protected)
            # Now let's decode the base64 and load it as a dictionary so we can get the length
            protected = base64.b64decode(protected)
            protected = json.loads(protected)
            # This is the length of the signed portion of the Manifest, except for a trailing
            # newline and closing curly brace.
            signed_length = protected['formatLength']
            # The formatTail key indexes a base64 encoded string that represents the end of the
            # original Manifest before signatures. We will need to add this string back to the
            # trimmed Manifest to get the correct digest. We'll do this as a one liner since it is
            # a very similar process to what we've just done above to get the protected block
            # decoded.
            signed_tail = base64.b64decode(UnitMixin._pad_unpadded_b64(protected['formatTail']))
            # Now we can reconstruct the original Manifest that the digest should be based on.
            manifest = manifest[:signed_length] + signed_tail
        hasher = getattr(hashlib, algorithm)
        return "{a}:{d}".format(a=algorithm, d=hasher(manifest).hexdigest())

    @staticmethod
    def _pad_unpadded_b64(unpadded_b64):
        """
        Docker has not included the required padding at the end of the base64 encoded
        'protected' block, or in some encased base64 within it. This function adds the correct
        number of ='s signs to the unpadded base64 text so that it can be decoded with Python's
        base64 library.

        :param unpadded_b64: The unpadded base64 text
        :type  unpadded_b64: basestring
        :return:             The same base64 text with the appropriate number of ='s symbols
                             appended
        :rtype:              basestring
        """
        # The Pulp team has not observed any newlines or spaces within the base64 from Docker, but
        # Docker's own code does this same operation so it seemed prudent to include it here.
        # See lines 167 to 168 here:
        # https://github.com/docker/libtrust/blob/9cbd2a1374f46905c68a4eb3694a130610adc62a/util.go
        unpadded_b64 = unpadded_b64.replace('\n', '').replace(' ', '')
        # It is illegal base64 for the remainder to be 1 when the length of the block is
        # divided by 4.
        if len(unpadded_b64) % 4 == 1:
            raise ValueError(_('Invalid base64: {t}').format(t=unpadded_b64))
        # Add back the missing padding characters, based on the length of the encoded string
        paddings = {0: '', 2: '==', 3: '='}
        return unpadded_b64 + paddings[len(unpadded_b64) % 4]


class Manifest(pulp_models.FileContentUnit, UnitMixin):
    """
    This model represents a Docker v2, Schema 1 Image Manifest and Schema 2 Image Manifest.

    https://github.com/docker/distribution/blob/release/2.0/docs/spec/manifest-v2-1.md
    https://github.com/docker/distribution/blob/release/2.3/docs/spec/manifest-v2-2.md#image-manifest
    """
    digest = mongoengine.StringField(required=True)
    schema_version = mongoengine.IntField(required=True)
    fs_layers = mongoengine.ListField(field=mongoengine.EmbeddedDocumentField(FSLayer),
                                      required=True)
    config_layer = mongoengine.StringField()

    # For backward compatibility
    _ns = mongoengine.StringField(
        default='units_{type_id}'.format(type_id=constants.MANIFEST_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True, default=constants.MANIFEST_TYPE_ID)

    unit_key_fields = ('digest',)
    meta = {'collection': 'units_{type_id}'.format(type_id=constants.MANIFEST_TYPE_ID),
            'indexes': [],
            'allow_inheritance': False}

    @classmethod
    def from_json(cls, manifest_json, digest):
        """
        Construct and return a Docker Manifest from the given JSON document.

        :param manifest_json: A JSON document describing a DockerManifest object as defined by the
                              Docker v2, Schema 1 Image Manifest documentation.
        :type  manifest_json: basestring
        :param digest:        The content digest of the manifest, as described at
                              https://docs.docker.com/registry/spec/api/#content-digests
        :type  digest:        basestring

        :return:              An initialized Docker Manifest object
        :rtype:               pulp_docker.plugins.models.Manifest
        """
        manifest = json.loads(manifest_json)
        config_layer = None
        try:
            fs_layers = [FSLayer(blob_sum=layer['digest'],
                         layer_type=layer['mediaType']) for layer in manifest['layers']]
            config_layer = manifest['config']['digest']
        except KeyError:
            fs_layers = [FSLayer(blob_sum=layer['blobSum']) for layer in manifest['fsLayers']]
        return cls(digest=digest, schema_version=manifest['schemaVersion'], fs_layers=fs_layers,
                   config_layer=config_layer)

    def get_symlink_name(self):
        """
        Provides the name that should be used when creating a symlink.
        :return: file name as it appears in a published repository
        :rtype: str
        """
        return '/'.join(('manifests', str(self.schema_version), self.digest))


class ManifestList(pulp_models.FileContentUnit, UnitMixin):
    """
    This model represents a Docker v2, Schema 2 Manifest list, as described here:

    https://github.com/docker/distribution/blob/release/2.3/docs/spec/manifest-v2-2.md#manifest-list
    """
    digest = mongoengine.StringField(required=True)
    schema_version = mongoengine.IntField(required=True)
    manifests = mongoengine.ListField(mongoengine.StringField(), required=True)
    amd64_digest = mongoengine.StringField()
    amd64_schema_version = mongoengine.IntField()

    # For backward compatibility
    _ns = mongoengine.StringField(
        default='units_{type_id}'.format(type_id=constants.MANIFEST_LIST_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True,
                                               default=constants.MANIFEST_LIST_TYPE_ID)

    unit_key_fields = ('digest',)

    meta = {'collection': 'units_{type_id}'.format(type_id=constants.MANIFEST_LIST_TYPE_ID),
            'indexes': [],
            'allow_inheritance': False}

    @classmethod
    def from_json(cls, manifest_list_json, digest):
        """
        Construct and return a Docker ManifestList from the given JSON document.

        :param manifest_list_json: A JSON document describing a ManifestList object as defined by
                                   the Docker v2, Schema 2 Manifest List documentation.
        :type  manifest_list_json: basestring
        :param digest:             The content digest of the manifest, as described at
                                   https://docs.docker.com/registry/spec/api/#content-digests
        :type  digest:             basestring

        :return:                   An initialized ManifestList object
        :rtype:                    pulp_docker.plugins.models.ManifestList
        """
        manifest_list = json.loads(manifest_list_json)
        # we will store here the digests of image manifests that manifest list contains
        manifests = []
        amd64_digest = None
        amd64_schema_version = None
        for image_man in manifest_list['manifests']:
            manifests.append(image_man['digest'])
            # we need to store separately the digest for the amd64 linux image manifest for later
            # conversion. There can be several image manifests that would match the ^ criteria but
            # we would keep just the first occurence.
            if image_man['platform']['architecture'] == 'amd64' and \
                    image_man['platform']['os'] == 'linux' and not amd64_digest:
                amd64_digest = image_man['digest']
                if image_man['mediaType'] == constants.MEDIATYPE_MANIFEST_S2:
                    amd64_schema_version = 2
                else:
                    amd64_schema_version = 1

        return cls(digest=digest, schema_version=manifest_list['schemaVersion'],
                   manifests=manifests, amd64_digest=amd64_digest,
                   amd64_schema_version=amd64_schema_version)

    @staticmethod
    def check_json(manifest_list_json):
        """
        Check the structure of a manifest list json file.

        This function is a sanity check to make sure the JSON contains the
        correct structure. It does not validate with the database.

        :param manifest_list_json: A JSON document describing a ManifestList object as defined by
                                   the Docker v2, Schema 2 Manifest List documentation.
        :type  manifest_list_json: basestring

        :raises PulpCodedValidationException: DKR1011 if manifest_list_json is invalid JSON
        :raises PulpCodedValidationException: DKR1012 if Manifest List has an invalid mediaType
        :raises PulpCodedValidationException: DKR1014 if any of the listed Manifests contain invalid
                                              mediaType
        :raises PulpCodedValidationException: DKR1015 if Manifest List does not have all required
                                              fields.
        :raises PulpCodedValidationException: DKR1016 if any Image Manifest in the list does not
                                              have all required fields.
        """
        try:
            manifest_list = json.loads(manifest_list_json)
        except ValueError:
            raise PulpCodedValidationException(error_code=error_codes.DKR1011)

        for field in MANIFEST_LIST_REQUIRED_FIELDS:
            if field not in manifest_list:
                raise PulpCodedValidationException(error_code=error_codes.DKR1015,
                                                   field=field)

        if manifest_list['mediaType'] != constants.MEDIATYPE_MANIFEST_LIST:
            raise PulpCodedValidationException(error_code=error_codes.DKR1012,
                                               media_type=manifest_list['mediaType'])

        for image_manifest_dict in manifest_list['manifests']:
            for field in IMAGE_MANIFEST_REQUIRED_FIELDS:
                if field not in image_manifest_dict:
                    raise PulpCodedValidationException(error_code=error_codes.DKR1016,
                                                       field=field)
            for field in IMAGE_MANIFEST_REQUIRED_PLATFORM_SUBFIELDS:
                if field not in image_manifest_dict['platform']:
                    subfield = "platform.{field}".format(field=field)
                    raise PulpCodedValidationException(error_code=error_codes.DKR1016,
                                                       field=subfield)

            if image_manifest_dict['mediaType'] not in [constants.MEDIATYPE_MANIFEST_S2,
                                                        constants.MEDIATYPE_MANIFEST_S1,
                                                        constants.MEDIATYPE_SIGNED_MANIFEST_S1]:
                raise PulpCodedValidationException(error_code=error_codes.DKR1014,
                                                   digest=image_manifest_dict['digest'])

    def get_symlink_name(self):
        """
        Provides the name that should be used when creating a symlink.
        :return: file name as it appears in a published repository
        :rtype: str
        """
        return '/'.join(('manifests', 'list', self.digest))


class TagQuerySet(querysets.QuerySetPreventCache):
    """
    This is a custom QuerySet for the Tag model that allows it to have some custom behavior.
    """
    def tag_manifest(self, repo_id, tag_name, manifest_digest, schema_version, manifest_type,
                     pulp_user_metadata=None):
        """
        Tag a Manifest in a repository by trying to create a Tag object with the given tag_name and
        repo_id referencing the given Manifest digest. Tag objects have a uniqueness constraint on
        their repo_id and name attribute, so if the Tag cannot be created we will update the
        existing Tag to reference the given Manifest digest instead.

        The resulting Tag will be returned in either case.

        :param repo_id:         The repository id that this Tag is to be placed in
        :type  repo_id:         basestring
        :param tag_name:        The name of the tag to create or update in the repository
        :type  tag_name:        basestring
        :param manifest_digest: The digest of the Manifest that is being tagged
        :type  manifest_digest: basestring
        :param schema_version:  The schema version  of the Manifest that is being tagged
        :type  schema_version:  int
        :param manifest_type:  image manifest or manifest list type
        :type  manifest_type:  basestring
        :return:                If a new Tag is created it is returned. Otherwise None is returned.
        :rtype:                 Either a pulp_docker.plugins.models.Tag or None
        """
        unit_keys = dict(
            name=tag_name, repo_id=repo_id,
            schema_version=schema_version, manifest_type=manifest_type)
        unit_md = dict(manifest_digest=manifest_digest)
        if pulp_user_metadata is not None:
            # Syncing should not overwrite existing pulp_user_metadata
            unit_md.update(pulp_user_metadata=pulp_user_metadata)
        try:
            tag = Tag(**dict(unit_keys, **unit_md))
            tag.save()
        except mongoengine.NotUniqueError:
            # There is already a Tag with the given unique keys, so let's just make sure its
            # other fields are updated
            tag = Tag.objects.get(**unit_keys)
            changed = False
            for k, v in unit_md.items():
                if getattr(tag, k) != v:
                    changed = True
                    setattr(tag, k, v)
            if changed:
                # we don't need to set _last_updated field because it is done with pre_save signal
                tag.save()
        return tag


class Tag(pulp_models.ContentUnit):
    """
    This class is used to represent Docker v2 tags. Docker tags are labels within a repository that
    point at Manifests by digest. This model represents the label with its name field, the digest
    its manifest_digest field, and the repository with its repo_id field.

    Tags must be unique by name inside a given repository. Pulp does not currently have a way for
    plugin authors to express model uniqueness within a repository, so this model includes a repo_id
    field so that it can have a uniqueness constraint on repo_id and name.
    """
    # This is the tag's name, or label
    name = mongoengine.StringField(required=True)
    # This is the digest of the Manifest that this Tag references
    manifest_digest = mongoengine.StringField(required=True)
    # This is the repository that this Tag exists in. It is only here so that we can form a
    # uniqueness constraint that enforces that the Tag's name can only appear once in each
    # repository.
    repo_id = mongoengine.StringField(required=True)
    schema_version = mongoengine.IntField(required=True)
    manifest_type = mongoengine.StringField(required=True)

    # For backward compatibility
    _ns = mongoengine.StringField(default='units_{type_id}'.format(type_id=constants.TAG_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True, default=constants.TAG_TYPE_ID)

    unit_key_fields = ('name', 'repo_id', 'schema_version', 'manifest_type')

    # Pulp has a bug where it does not install a uniqueness constraint for us based on the
    # unit_key_fields we defined above: https://pulp.plan.io/issues/1477
    # Until that issue is resolved, we need to install a uniqueness constraint here.
    meta = {'collection': 'units_{type_id}'.format(type_id=constants.TAG_TYPE_ID),
            'allow_inheritance': False,
            'queryset_class': TagQuerySet}
