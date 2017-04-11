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

from pulp_docker.common import constants


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


class Manifest(pulp_models.FileContentUnit):
    """
    This model represents a Docker v2, Schema 1 Image Manifest, as described here:

    https://github.com/docker/distribution/blob/release/2.0/docs/spec/manifest-v2-1.md
    """
    digest = mongoengine.StringField(required=True)
    name = mongoengine.StringField(required=True)
    tag = mongoengine.StringField()
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
            'indexes': ['name', 'tag'],
            'allow_inheritance': False}

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
            protected = Manifest._pad_unpadded_b64(protected)
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
            signed_tail = base64.b64decode(Manifest._pad_unpadded_b64(protected['formatTail']))
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

    @classmethod
    def from_json(cls, manifest_json, digest, tag, upstream_name):
        """
        Construct and return a DockerManifest from the given JSON document.

        :param manifest_json: A JSON document describing a DockerManifest object as defined by the
                              Docker v2, Schema 1 Image Manifest documentation.
        :type  manifest_json: basestring
        :param digest:        The content digest of the manifest, as described at
                              https://docs.docker.com/registry/spec/api/#content-digests
        :type  digest:        basestring
        :param tag:           Tag of the image repository
        :type  tag:           basestring
        :param upstream_name: Name of the upstream repository
        :type  upstream_name: basestring

        :return:              An initialized DockerManifest object
        :rtype:               pulp_docker.common.models.DockerManifest
        """
        # manifest schema version 2 does not contain tag and name information
        # we need to retrieve them from other sources, that's why there were added 2 more
        # parameters in this method
        manifest = json.loads(manifest_json)
        config_layer = None
        try:
            fs_layers = [FSLayer(blob_sum=layer['digest']) for layer in manifest['layers']]
            config_layer = manifest['config']['digest']
        except KeyError:
            fs_layers = [FSLayer(blob_sum=layer['blobSum']) for layer in manifest['fsLayers']]
        return cls(digest=digest, name=upstream_name, tag=tag,
                   schema_version=manifest['schemaVersion'], fs_layers=fs_layers,
                   config_layer=config_layer)

    def get_symlink_name(self):
        """
        Provides the name that should be used when creating a symlink.
        :return: file name as it appears in a published repository
        :rtype: str
        """
        return '/'.join(('manifests', str(self.schema_version), self.digest))


class TagQuerySet(querysets.QuerySetPreventCache):
    """
    This is a custom QuerySet for the Tag model that allows it to have some custom behavior.
    """
    def tag_manifest(self, repo_id, tag_name, manifest_digest, schema_version):
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
        :return:                If a new Tag is created it is returned. Otherwise None is returned.
        :rtype:                 Either a pulp_docker.plugins.models.Tag or None
        """
        try:
            tag = Tag(name=tag_name, manifest_digest=manifest_digest, repo_id=repo_id,
                      schema_version=schema_version)
            tag.save()
        except mongoengine.NotUniqueError:
            # There is already a Tag with the given name and repo_id, so let's just make sure it's
            # digest is updated. No biggie.
            # Let's check if the manifest_digest changed
            tag = Tag.objects.get(name=tag_name, repo_id=repo_id, schema_version=schema_version)
            if tag.manifest_digest != manifest_digest:
                tag.manifest_digest = manifest_digest
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

    # For backward compatibility
    _ns = mongoengine.StringField(default='units_{type_id}'.format(type_id=constants.TAG_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True, default=constants.TAG_TYPE_ID)

    unit_key_fields = ('name', 'repo_id', 'schema_version')

    # Pulp has a bug where it does not install a uniqueness constraint for us based on the
    # unit_key_fields we defined above: https://pulp.plan.io/issues/1477
    # Until that issue is resolved, we need to install a uniqueness constraint here.
    meta = {'collection': 'units_{type_id}'.format(type_id=constants.TAG_TYPE_ID),
            'allow_inheritance': False,
            'queryset_class': TagQuerySet}
