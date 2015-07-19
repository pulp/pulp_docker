"""
This modules contains tests for pulp_docker.common.models.
"""
import math
import os
import unittest

from pulp_docker.common import models


class TestBasics(unittest.TestCase):
    def test_init_info(self):
        image = models.Image('abc', 'xyz', 1024)

        self.assertEqual(image.image_id, 'abc')
        self.assertEqual(image.parent_id, 'xyz')
        self.assertEqual(image.size, 1024)

    def test_unit_key(self):
        image = models.Image('abc', 'xyz', 1024)

        self.assertEqual(image.unit_key, {'image_id': 'abc'})

    def test_relative_path(self):
        image = models.Image('abc', 'xyz', 1024)

        self.assertEqual(image.relative_path, 'abc')

    def test_metadata(self):
        image = models.Image('abc', 'xyz', 1024)
        metadata = image.unit_metadata

        self.assertEqual(metadata.get('parent_id'), 'xyz')
        self.assertEqual(metadata.get('size'), 1024)


class TestManifest(unittest.TestCase):
    """
    This class contains tests for the Manifest class.
    """
    def test___init__(self):
        """
        Assert correct operation of the __init__() method.
        """
        name = 'name'
        tag = 'tag'
        architecture = 'x86_65'  # it's one better
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [{'layer_1': 'rsum:jsf'}]
        history = [{'v1Compatibility': 'not sure what goes here but something does'}]
        schema_version = 1
        signatures = [{'some': 'signature'}]

        m = models.Manifest(digest, name, tag, architecture, fs_layers, history,
                            schema_version, signatures)

        self.assertEqual(m.name, name)
        self.assertEqual(m.tag, tag)
        self.assertEqual(m.architecture, architecture)
        self.assertEqual(m.digest, digest)
        self.assertEqual(m.fs_layers, fs_layers)
        self.assertEqual(m.history, history)
        self.assertEqual(m.signatures, signatures)
        self.assertEqual(m.schema_version, schema_version)

    def test___init___bad_schema(self):
        """
        Assert correct operation of the __init__() method with an invalid (i.e., != 1) schema
        version.
        """
        name = 'name'
        tag = 'tag'
        architecture = 'x86_65'  # it's one better
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [{'layer_1': 'rsum:jsf'}]
        history = [{'v1Compatibility': 'not sure what goes here but something does'}]
        schema_version = math.pi
        signatures = [{'some': 'signature'}]

        self.assertRaises(ValueError, models.Manifest, name, tag, architecture, digest,
                          fs_layers, history, schema_version, signatures)

    def test_from_json(self):
        """
        Assert correct operation of the from_json class method.
        """
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        example_manifest_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                                             'example_docker_v2_manifest.json')
        with open(example_manifest_path) as manifest_file:
            manifest = manifest_file.read()

        m = models.Manifest.from_json(manifest, digest)

        self.assertEqual(m.name, 'hello-world')
        self.assertEqual(m.tag, 'latest')
        self.assertEqual(m.architecture, 'amd64')
        self.assertEqual(m.digest, digest)
        self.assertEqual(m.schema_version, 1)
        # We will just spot check the following attributes, as they are complex data structures
        self.assertEqual(len(m.fs_layers), 4)
        self.assertEqual(
            m.fs_layers[1],
            {"blobSum": "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef"})
        self.assertEqual(len(m.history), 2)
        self.assertTrue('],\"Image\":\"31cbccb51277105ba3ae35ce' in m.history[0]['v1Compatibility'])
        self.assertEqual(len(m.signatures), 1)
        self.assertTrue('XREm0L8WNn27Ga_iE_vRnTxVMhhYY0Zst_FfkKopg' in m.signatures[0]['signature'])

    def test_metadata(self):
        """
        Assert correct operation of the metadata property.
        """
        name = 'name'
        tag = 'tag'
        architecture = 'x86_65'  # it's one better
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [{'layer_1': 'rsum:jsf'}]
        history = [{'v1Compatibility': 'not sure what goes here but something does'}]
        schema_version = 1
        signatures = [{'some': 'signature'}]
        m = models.Manifest(digest, name, tag, architecture, fs_layers, history,
                            schema_version, signatures)

        metadata = m.metadata

        self.assertEqual(
            metadata,
            {'name': name, 'tag': tag, 'architecture': architecture, 'fs_layers': fs_layers,
             'history': history, 'schema_version': schema_version, 'signatures': signatures})

    def test_relative_path(self):
        """
        The Manifest's relative path should be its digest.
        """
        name = 'name'
        tag = 'tag'
        architecture = 'x86_65'  # it's one better
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [{'layer_1': 'rsum:jsf'}]
        history = [{'v1Compatibility': 'not sure what goes here but something does'}]
        schema_version = 1
        signatures = [{'some': 'signature'}]
        m = models.Manifest(digest, name, tag, architecture, fs_layers, history,
                            schema_version, signatures)

        relative_path = m.relative_path

        self.assertEqual(relative_path, digest)

    def test_unit_key(self):
        """
        Assert correct operation of the unit_key property.
        """
        name = 'name'
        tag = 'tag'
        architecture = 'x86_65'  # it's one better
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [{'layer_1': 'rsum:jsf'}]
        history = [{'v1Compatibility': 'not sure what goes here but something does'}]
        schema_version = 1
        signatures = [{'some': 'signature'}]
        m = models.Manifest(digest, name, tag, architecture, fs_layers, history,
                            schema_version, signatures)

        unit_key = m.unit_key

        self.assertEqual(unit_key, {'digest': digest})
