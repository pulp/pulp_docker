"""
This module contains common model objects that are used to describe the data types used in the
pulp_docker plugins.
"""
import json

from pulp_docker.common import constants


class Blob(object):
    """
    This class is used to represent Docker v2 blobs.
    """
    TYPE_ID = 'docker_blob'

    def __init__(self, digest):
        """
        Initialize the Blob.

        :param image_id:    This field will store the blob's digest.
        :type  image_id:    basestring
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
        return self.image_id

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
    TYPE_ID = 'docker_manifest'

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
