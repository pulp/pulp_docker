"""
This module contains common model objects that are used to describe the data types used in the
pulp_docker plugins.
"""
import base64
import hashlib
import json
from gettext import gettext as _

import mongoengine
from pulp.server.db import model as pulp_models

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

    # For backward compatibility
    _ns = mongoengine.StringField(
        default='units_{type_id}'.format(type_id=constants.MANIFEST_TYPE_ID))
    _content_type_id = mongoengine.StringField(required=True, default=constants.MANIFEST_TYPE_ID)

    unit_key_fields = ('digest',)

    meta = {'collection': 'units_{type_id}'.format(type_id=constants.MANIFEST_TYPE_ID),
            'indexes': ['name', 'tag'],
            'allow_inheritance': False}

    def save(self):
        """
        Save the model to the database, after validating that the schema version is exactly 1.
        """
        if self.schema_version != 1:
            raise ValueError(
                "The DockerManifest class only supports Docker v2, Schema 1 manifests.")
        super(Manifest, self).save()

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
    def from_json(cls, manifest_json, digest):
        """
        Construct and return a DockerManifest from the given JSON document.

        :param manifest_json: A JSON document describing a DockerManifest object as defined by the
                              Docker v2, Schema 1 Image Manifest documentation.
        :type  manifest_json: basestring
        :param digest:        The content digest of the manifest, as described at
                              https://docs.docker.com/registry/spec/api/#content-digests
        :type  digest:        basestring

        :return:              An initialized DockerManifest object
        :rtype:               pulp_docker.common.models.DockerManifest
        """
        manifest = json.loads(manifest_json)
        fs_layers = [FSLayer(blob_sum=layer['blobSum']) for layer in manifest['fsLayers']]
        return cls(digest=digest, name=manifest['name'], tag=manifest['tag'],
                   schema_version=manifest['schemaVersion'], fs_layers=fs_layers)
