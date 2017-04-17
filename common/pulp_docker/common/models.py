"""
This module contains common model objects that are used to describe the data types used in the
pulp_docker plugins.
"""
import base64
import hashlib
import json
import os
from gettext import gettext as _

from pulp_docker.common import constants


class Blob(object):
    """
    This class is used to represent Docker v2 blobs.
    """
    TYPE_ID = constants.BLOB_TYPE_ID

    def __init__(self, digest):
        """
        Initialize the Blob.

        :param digest:    This field will store the blob's digest.
        :type  digest:    basestring
        """
        self.digest = digest

    @property
    def unit_key(self):
        """
        Return the Blob's unit key.

        :return:    unit key
        :rtype:     dict
        """
        return {
            'digest': self.digest
        }

    @property
    def metadata(self):
        """
        A blob has no metadata, so return an empty dictionary.

        :return: Empty dictionary
        :rtype:  dict
        """
        return {}

    @property
    def relative_path(self):
        """
        Return the Blob's relative path for filesystem storage.

        :return:    the relative path to where this Blob should live
        :rtype:     basestring
        """
        return self.digest


class Image(object):
    """
    This class is used to represent Docker v1 images.
    """
    TYPE_ID = constants.IMAGE_TYPE_ID

    def __init__(self, image_id, parent_id, size):
        """
        Initialize the Image.

        :param image_id:  The Image's id.
        :type  image_id:  basestring
        :param parent_id: parent's unique image ID
        :type  parent_id: basestring
        :param size:      size of the image in bytes, as reported by docker.
                          This can be None, because some very old docker images
                          do not contain it in their metadata.
        :type  size:      int or NoneType
        """
        self.image_id = image_id
        self.parent_id = parent_id
        self.size = size

    @property
    def unit_key(self):
        """
        Return the Image's unit key.

        :return:    unit key
        :rtype:     dict
        """
        return {
            'image_id': self.image_id
        }

    @property
    def relative_path(self):
        """
        Return the Image's relative path for filesystem storage.

        :return:    the relative path to where this image's directory should live
        :rtype:     basestring
        """
        return os.path.join(self.TYPE_ID, self.image_id)

    @property
    def unit_metadata(self):
        """
        Return the Image's Metadata.

        :return:    a subset of the complete docker metadata about this image,
                    including only what pulp_docker cares about
        :rtype:     dict
        """
        return {
            'parent_id': self.parent_id,
            'size': self.size
        }


class Manifest(object):
    """
    This model represents a Docker v2, Schema 1 Image Manifest, as described here:

    https://github.com/docker/distribution/blob/release/2.0/docs/spec/manifest-v2-1.md
    """
    TYPE_ID = constants.MANIFEST_TYPE_ID

    def __init__(self, digest, name, tag, architecture, fs_layers, history, schema_version,
                 signatures):
        """
        Initialize the DockerManifest model with the given attributes. See the class docblock above
        for a link to the Docker documentation that covers these attributes. Note that this class
        attempts to follow Python naming guidelines for the class attributes, while allowing
        Docker's camelCase names for the inner values on dictionaries.

        :param digest:         The content digest of the manifest, as described at
                               https://docs.docker.com/registry/spec/api/#content-digests
        :type  digest:         basestring
        :param name:           The name of the Manifest's repository
        :type  name:           basestring
        :param tag:            The Manifest's tag
        :type  tag:            basestring
        :param architecture:   The host architecture on which the image is intended to run
        :type  architecture:   basestring
        :param fs_layers:      A list of dictionaries. Each dictionary contains one key-value pair
                               that represents a layer (a Blob) of the image. The key is blobSum,
                               and the value is the digest of the referenced layer. See the
                               documentation referenced in the class docblock for more information.
        :type  fs_layers:      list
        :param history:        This is a list of unstructured historical data for v1 compatibility.
                               Each member is a dictionary with a "v1Compatibility" key that indexes
                               a string.
        :type  history:        list
        :param schema_version: The image manifest schema that this image follows
        :type  schema_version: int
        :param signatures:     A list of cryptographic signatures on the image. See the
                               documentation in the in this class's docblock for information about
                               its formatting.
        :type  signatures:     list
        """
        self.digest = digest
        self.name = name
        self.tag = tag
        self.architecture = architecture
        self.fs_layers = fs_layers
        self.history = history
        self.signatures = signatures

        if schema_version != 1:
            raise ValueError(
                "The DockerManifest class only supports Docker v2, Schema 1 manifests.")
        self.schema_version = schema_version

    @staticmethod
    def digest(manifest, algorithm='sha256'):
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
        return cls(
            digest=digest, name=manifest['name'], tag=manifest['tag'],
            architecture=manifest['architecture'], fs_layers=manifest['fsLayers'],
            history=manifest['history'], schema_version=manifest['schemaVersion'],
            signatures=manifest['signatures'])

    @property
    def metadata(self):
        """
        Return the Manifest's metadata, which is all attributes that are not part of the unit key.

        :return: metadata
        :rtype:  dict
        """
        return {
            'fs_layers': self.fs_layers, 'history': self.history, 'signatures': self.signatures,
            'schema_version': self.schema_version, 'name': self.name, 'tag': self.tag,
            'architecture': self.architecture}

    @property
    def relative_path(self):
        """
        The relative path where this Manifest should live

        :return: the relative path to where this Manifest should live
        :rtype:  basestring
        """
        return self.digest

    @property
    def unit_key(self):
        """
        Return the Manifest's unit key, which is the digest.

        :return: unit key
        :rtype:  dict
        """
        return {'digest': self.digest}
