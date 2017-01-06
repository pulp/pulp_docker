"""
This modules contains tests for pulp_docker.common.models.
"""
import os
import unittest

from pulp_docker.plugins import models


class TestImage(unittest.TestCase):
    def test_init_info(self):
        image = models.Image(image_id='abc', parent_id='xyz', size=1024)

        self.assertEqual(image.image_id, 'abc')
        self.assertEqual(image.parent_id, 'xyz')
        self.assertEqual(image.size, 1024)

    def test_unit_key(self):
        image = models.Image(image_id='abc', parent_id='xyz', size=1024)

        self.assertEqual(image.unit_key, {'image_id': 'abc'})

    def test_list_files(self):
        unit = models.Image()
        unit.set_storage_path()
        names = ('ancestry', 'json', 'layer')
        files = list(unit.list_files())
        self.assertEqual(files, [os.path.join(unit.storage_path, n) for n in names])


class TestBlob(unittest.TestCase):
    """
    This class contains tests for the Blob class.
    """
    def test___init__(self):
        """
        Assert correct behavior from the __init__() method.
        """
        digest = 'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef'

        blob = models.Blob(digest=digest)

        self.assertEqual(blob.digest, digest)

    def test_unit_key(self):
        """
        Assert correct behavior from the unit_key() method.
        """
        digest = 'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef'

        blob = models.Blob(digest=digest)

        self.assertEqual(blob.unit_key, {'digest': digest})


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
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [models.FSLayer(blob_sum='rsum:jsf')]
        schema_version = 2
        config_layer = 'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef'

        m = models.Manifest(digest=digest, name=name, tag=tag, fs_layers=fs_layers,
                            schema_version=schema_version, config_layer=config_layer)

        self.assertEqual(m.name, name)
        self.assertEqual(m.tag, tag)
        self.assertEqual(m.digest, digest)
        self.assertEqual(m.fs_layers, fs_layers)
        self.assertEqual(m.schema_version, schema_version)
        self.assertEqual(m.config_layer, config_layer)

    def test_from_json_schema1(self):
        """
        Assert correct operation of the from_json class method.
        """
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        example_manifest_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data',
                                             'manifest_repeated_layers.json')
        with open(example_manifest_path) as manifest_file:
            manifest = manifest_file.read()

        m = models.Manifest.from_json(manifest, digest, 'latest', 'hello-world')

        self.assertEqual(m.name, 'hello-world')
        self.assertEqual(m.tag, 'latest')
        self.assertEqual(m.digest, digest)
        self.assertEqual(m.schema_version, 1)
        self.assertEqual(m.config_layer, None)
        # We will just spot check the following attributes, as they are complex data structures
        self.assertEqual(len(m.fs_layers), 4)
        self.assertEqual(
            m.fs_layers[1].blob_sum,
            "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef")

    def test_from_json_schema2(self):
        """
        Assert correct operation of the from_json class method.
        """
        digest = 'sha256:817a12c32a39bbe394944ba49de563e085f1d3c5266eb8e9723256bc4448680e'
        config_layer = 'sha256:7968321274dc6b6171697c33df7815310468e694ac5be0ec03ff053bb135e768'
        example_manifest_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data',
                                             'manifest_schema2_one_layer.json')
        with open(example_manifest_path) as manifest_file:
            manifest = manifest_file.read()

        m = models.Manifest.from_json(manifest, digest, 'latest', 'hello-world')

        self.assertEqual(m.name, 'hello-world')
        self.assertEqual(m.tag, 'latest')
        self.assertEqual(m.digest, digest)
        self.assertEqual(m.schema_version, 2)
        self.assertEqual(m.config_layer, config_layer)
        # We will just spot check the following attributes, as they are complex data structures
        self.assertEqual(len(m.fs_layers), 1)
        self.assertEqual(
            m.fs_layers[0].blob_sum,
            "sha256:4b0bc1c4050b03c95ef2a8e36e25feac42fd31283e8c30b3ee5df6b043155d3c")

    def test_unit_key(self):
        """
        Assert correct operation of the unit_key property.
        """
        name = 'name'
        tag = 'tag'
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [models.FSLayer(blob_sum='rsum:jsf')]
        schema_version = 1
        manifest = models.Manifest(name=name, tag=tag, digest=digest,
                                   fs_layers=fs_layers, schema_version=schema_version)

        unit_key = manifest.unit_key

        self.assertEqual(unit_key, {'digest': digest})


class TestTag(unittest.TestCase):
    """
    This class contains tests for the Tag class.
    """
    def test___init__(self):
        """
        Assert correct operation of the __init__() method.
        """
        name = 'name'
        manifest_digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        repo_id = 'hello-world'
        schema_version = 2

        m = models.Tag(name=name, manifest_digest=manifest_digest, repo_id=repo_id,
                       schema_version=schema_version)

        self.assertEqual(m.name, name)
        self.assertEqual(m.manifest_digest, manifest_digest)
        self.assertEqual(m.repo_id, repo_id)
        self.assertEqual(m.schema_version, schema_version)

    def test_unit_key(self):
        """
        Assert correct operation of the unit_key property.
        """
        name = 'name'
        manifest_digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        repo_id = 'hello-world'
        schema_version = 2
        m = models.Tag(name=name, manifest_digest=manifest_digest, repo_id=repo_id,
                       schema_version=schema_version)

        unit_key = m.unit_key

        self.assertEqual(unit_key, {'name': name, 'repo_id': repo_id,
                                    'schema_version': schema_version})
