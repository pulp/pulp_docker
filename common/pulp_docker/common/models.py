"""
This module contains common model objects that are used to describe the data types used in the
pulp_docker plugins.
"""
import json
import os

from pulp_docker.common import constants


class DockerImage(object):
    TYPE_ID = constants.IMAGE_TYPE_ID

    def __init__(self, image_id, parent_id, size):
        """
        :param image_id:    unique image ID
        :type  image_id:    basestring
        :param parent_id:   parent's unique image ID
        :type  parent_id:   basestring
        :param size:        size of the image in bytes, as reported by docker.
                            This can be None, because some very old docker images
                            do not contain it in their metadata.
        :type  size:        int or NoneType
        """
        self.image_id = image_id
        self.parent_id = parent_id
        self.size = size

    @property
    def unit_key(self):
        """
        :return:    unit key
        :rtype:     dict
        """
        return {
            'image_id': self.image_id
        }

    @property
    def relative_path(self):
        """
        :return:    the relative path to where this image's directory should live
        :rtype:     basestring
        """
        return os.path.join(self.TYPE_ID, self.image_id)

    @property
    def unit_metadata(self):
        """
        :return:    a subset of the complete docker metadata about this image,
                    including only what pulp_docker cares about
        :rtype:     dict
        """
        return {
            'parent_id': self.parent_id,
            'size': self.size
        }


class DockerManifest(object):
    """
    This model represents a Docker v2, Schema 1 Image Manifest, as described here:

    https://github.com/docker/distribution/blob/release/2.0/docs/spec/manifest-v2-1.md
    """
    TYPE_ID = 'docker_manifest'

    def __init__(self, name, tag, architecture, digest, fs_layers, history, schema_version,
                 signatures):
        """
        Initialize the DockerManifest model with the given attributes. See the class docblock above
        for a link to the Docker documentation that covers these attributes. Note that this class
        attempts to follow Python naming guidelines for the class attributes, while allowing
        Docker's camelCase names for the inner values on dictionaries.

        :param name:           The name of the image's repository
        :type  name:           basestring
        :param tag:            The image's tag
        :type  tag:            basestring
        :param architecture:   The host architecture on which the image is intended to run
        :type  architecture:   basestring
        :param digest:         The content digest of the manifest, as described at
                               https://docs.docker.com/registry/spec/api/#content-digests
        :type  digest:         basestring
        :param fs_layers:      A list of dictionaries. Each dictionary contains one key-value pair
                               that represents a layer of the image. The key is blobSum, and the
                               value is the digest of the referenced layer. See the documentation
                               referenced in the class docblock for more information.
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
        self.name = name
        self.tag = tag
        self.architecture = architecture
        self.digest = digest
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
            name=manifest['name'], tag=manifest['tag'], architecture=manifest['architecture'],
            digest=digest, fs_layers=manifest['fsLayers'], history=manifest['history'],
            schema_version=manifest['schemaVersion'], signatures=manifest['signatures'])

    @property
    def to_json(self):
        """
        Return a JSON document that represents the DockerManifest object.

        :return: A JSON document in the Docker v2, Schema 1 Image Manifest format
        :rtype:  basestring
        """
        manifest = {
            'name': self.name, 'tag': self.tag, 'architecture': self.architecture,
            'fsLayers': self.fs_layers, 'history': self.history,
            'schemaVersion': self.schema_version, 'signatures': self.signatures}
        return json.dumps(manifest)

    @property
    def unit_key(self):
        """
        Return the manifest's unit key. The unit key consists of the name, tag, architecture, and
        fs_layers attributes as described in the __init__() method above.

        :return: unit key
        :rtype:  dict
        """
        return {'name': self.name, 'tag': self.tag, 'architecture': self.architecture,
                'digest': self.digest}
