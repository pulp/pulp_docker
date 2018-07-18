"""
This modules contains tests for pulp_docker.common.models.
"""
import mock
import os
import unittest

from pulp_docker.plugins import models

from pulp.server.exceptions import PulpCodedValidationException


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
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [models.FSLayer(blob_sum='rsum:jsf')]
        schema_version = 2
        config_layer = 'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef'

        m = models.Manifest(digest=digest, fs_layers=fs_layers,
                            schema_version=schema_version, config_layer=config_layer)

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

        m = models.Manifest.from_json(manifest, digest)

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

        m = models.Manifest.from_json(manifest, digest)

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
        digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        fs_layers = [models.FSLayer(blob_sum='rsum:jsf')]
        schema_version = 1
        manifest = models.Manifest(digest=digest, fs_layers=fs_layers,
                                   schema_version=schema_version)

        unit_key = manifest.unit_key

        self.assertEqual(unit_key, {'digest': digest})


class TestManifestList(unittest.TestCase):
    """
    This class contains tests for the ManifestList class.
    """
    def test___init__(self):
        """
        Assert correct operation of the __init__() method.
        """
        digest = 'sha256:69fd2d3fa813bcbb3a572f1af80fe31a1710409e15dde91af79be62b37ab4f70'
        manifests = [
            models.EmbeddedManifest(
                digest='sha256:c55544de64a01e157b9d931f5db7a16554a14be19c367f91c9a8cdc46db086bf',
                os='linux',
                arch='amd64'),
            models.EmbeddedManifest(
                digest='sha256:de9576aa7f9ac6aff09029293ca23136011302c02e183e856a2cd6d37b84ab92',
                os='linux',
                arch='arm')]
        schema_version = 2
        amd64_digest = 'sha256:c55544de64a01e157b9d931f5db7a16554a14be19c367f91c9a8cdc46db086bf'
        amd64_schema_version = 2

        m = models.ManifestList(digest=digest, manifests=manifests,
                                schema_version=schema_version, amd64_digest=amd64_digest,
                                amd64_schema_version=amd64_schema_version)

        self.assertEqual(m.digest, digest)
        self.assertEqual(m.manifests, manifests)
        self.assertEqual(m.schema_version, schema_version)
        self.assertEqual(m.amd64_digest, amd64_digest)
        self.assertEqual(m.amd64_schema_version, amd64_schema_version)

    def test_from_json(self):
        """
        Assert correct operation of the from_json class method.
        """
        digest = 'sha256:69fd2d3fa813bcbb3a572f1af80fe31a1710409e15dde91af79be62b37ab4f70'
        example_manifest_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data',
                                             'manifest_list.json')
        with open(example_manifest_path) as manifest_file:
            manifest_list = manifest_file.read()

        m = models.ManifestList.from_json(manifest_list, digest)

        self.assertEqual(m.digest, digest)
        self.assertEqual(m.schema_version, 2)
        amd64_digest = 'sha256:c55544de64a01e157b9d931f5db7a16554a14be19c367f91c9a8cdc46db086bf'
        self.assertEqual(m.amd64_digest, amd64_digest)
        self.assertEqual(m.amd64_schema_version, 2)
        self.assertEqual(len(m.manifests), 2)

    def test_check_json_invalid_json(self):
        """
        Assert validation exception is raised if json is invalid.
        """
        invalid_json = "{'invalid':'json"
        with self.assertRaises(PulpCodedValidationException) as e:
            models.ManifestList.check_json(invalid_json)
        self.assertEqual(e.exception.error_code.code, 'DKR1011')

    def test_check_json_invalid_mediatype(self):
        """
        Assert validation exception is raised mediaType is not a Manifest List.
        """
        valid_json = """{
            "mediaType": "invalid_media_type",
            "digest": "required",
            "schemaVersion": 2,
            "manifests": "won't get this far"
        }"""
        with self.assertRaises(PulpCodedValidationException) as e:
            models.ManifestList.check_json(valid_json)
        self.assertEqual(e.exception.error_code.code, 'DKR1012')

    def test_check_json_invalid_manifest_mediatype(self):
        """
        Assert validation exception is raised if referenced manifests have invalid mediaType.
        """
        valid_json = """
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
                "manifests": [
                    {
                       "mediaType": "manifest.with.invalid.mediaType",
                       "size": 527,
                       "digest": "sha256:314fe5a71adb69a444ceb5a34223f63c68adc6b9bac589f6385810ffa462fd02",
                       "platform": {
                          "architecture": "amd64",
                          "os": "linux"
                       }
                    }
                ]
            }
        """  # noqa
        with self.assertRaises(PulpCodedValidationException) as e:
            models.ManifestList.check_json(valid_json)
        self.assertEqual(e.exception.error_code.code, 'DKR1014')

    def test_check_json_as_expected(self):
        """
        Assert no exceptions are raised for a valid ManifestList.
        """
        valid_json = """
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
                "manifests": [
                    {
                       "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                       "size": 527,
                       "digest": "sha256:314fe5a71adb69a444ceb5a34223f63c68adc6b9bac589f6385810ffa462fd02",
                       "platform": {
                          "architecture": "amd64",
                          "os": "linux"
                       }
                    },
                    {
                       "mediaType": "application/vnd.docker.distribution.manifest.v1+json",
                       "size": 527,
                       "digest": "sha256:314fe5a71adb69a444ceb5a34223f63c68adc6b9bac589f6385810ffa462fd02",
                       "platform": {
                          "architecture": "amd64",
                          "os": "linux"
                       }
                    }

                ]
            }
        """  # noqa
        models.ManifestList.check_json(valid_json)

    def test_unit_key(self):
        """
        Assert correct operation of the unit_key property.
        """
        digest = 'sha256:69fd2d3fa813bcbb3a572f1af80fe31a1710409e15dde91af79be62b37ab4f70'
        manifests = [
            {'digest': 'sha256:c55544de64a01e157b9d931f5db7a16554a14be19c367f91c9a8cdc46db086bf',
             'arch': 'amd64',
             'os': 'linux'},
            {'digest': 'sha256:de9576aa7f9ac6aff09029293ca23136011302c02e183e856a2cd6d37b84ab92',
             'arch': 'arm',
             'os': 'linux'}]
        schema_version = 2
        amd64_digest = 'sha256:c55544de64a01e157b9d931f5db7a16554a14be19c367f91c9a8cdc46db086bf'
        amd64_schema_version = 2

        m = models.ManifestList(digest=digest, manifests=manifests,
                                schema_version=schema_version, amd64_digest=amd64_digest,
                                amd64_schema_version=amd64_schema_version)

        unit_key = m.unit_key

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
        manifest_type = 'image'

        m = models.Tag(name=name, manifest_digest=manifest_digest, repo_id=repo_id,
                       schema_version=schema_version, manifest_type=manifest_type)

        self.assertEqual(m.name, name)
        self.assertEqual(m.manifest_digest, manifest_digest)
        self.assertEqual(m.repo_id, repo_id)
        self.assertEqual(m.schema_version, schema_version)
        self.assertEqual(m.manifest_type, manifest_type)

    def test_unit_key(self):
        """
        Assert correct operation of the unit_key property.
        """
        name = 'name'
        manifest_digest = 'sha256:6c3c624b58dbbcd3c0dd82b4c53f04194d1247c6eebdaab7c610cf7d66709b3b'
        repo_id = 'hello-world'
        schema_version = 2
        manifest_type = 'image'
        m = models.Tag(name=name, manifest_digest=manifest_digest, repo_id=repo_id,
                       schema_version=schema_version, manifest_type=manifest_type)

        unit_key = m.unit_key

        self.assertEqual(unit_key, {'name': name, 'repo_id': repo_id,
                                    'schema_version': schema_version,
                                    'manifest_type': manifest_type})

    @mock.patch("pulp_docker.plugins.models.Tag.save")
    @mock.patch("pulp_docker.plugins.models.Tag._get_db")
    def test_tag_manifest(self, _get_db, _Tag_save):
        fields = dict(
            tag_name="aaa",
            repo_id="fedora",
            schema_version=42,
            manifest_type="blip",
            manifest_digest="sha256:123",
        )
        m = models.Tag.objects.tag_manifest(**fields)
        # tag_name corresponds to name
        fields['name'] = fields.pop('tag_name')
        for fname, fval in fields.items():
            self.assertEquals(fval, getattr(m, fname))
        self.assertEquals({}, m.pulp_user_metadata)

    @mock.patch("pulp_docker.plugins.models.Tag.save")
    @mock.patch("pulp_docker.plugins.models.Tag._get_db")
    def test_tag_manifest__with_pulp_user_metadata(self, _get_db, _Tag_save):
        fields = dict(
            tag_name="aaa",
            repo_id="fedora",
            schema_version=42,
            manifest_type="blip",
            manifest_digest="sha256:123",
            pulp_user_metadata={'branch': 'master'},
        )
        m = models.Tag.objects.tag_manifest(**fields)
        # tag_name corresponds to name
        fields['name'] = fields.pop('tag_name')
        for fname, fval in fields.items():
            self.assertEquals(fval, getattr(m, fname))

    @mock.patch("pulp_docker.plugins.models.Tag.objects")
    @mock.patch("pulp_docker.plugins.models.Tag.save")
    @mock.patch("pulp_docker.plugins.models.Tag._get_db")
    def test_tag_manifest__update(self, _get_db, _Tag_save, _Tag_objects):
        # Raise exception first, then succeed
        _Tag_save.side_effect = [models.mongoengine.NotUniqueError(), None]
        fields = dict(
            tag_name="aaa",
            repo_id="fedora",
            schema_version=42,
            manifest_type="blip",
            manifest_digest="sha256:123",
            pulp_user_metadata={'branch': 'master'},
        )
        fields_old = dict(fields)
        # Change digest and pulp_user_metadata, they should be overwritten
        fields_old['manifest_digest'] = "sha13:1"
        fields_old['pulp_user_metadata'] = {}
        fields_old['name'] = fields_old.pop('tag_name')
        existing_tag = models.Tag(**fields_old)

        qs = models.TagQuerySet(existing_tag, None)
        _Tag_objects.get.return_value = existing_tag

        m = qs.tag_manifest(**fields)
        self.assertEquals(id(existing_tag), id(m))

        # tag_name corresponds to name
        fields['name'] = fields.pop('tag_name')

        unit_keys = dict((x, fields[x]) for x in existing_tag.unit_key_fields)
        _Tag_objects.get.assert_called_once_with(**unit_keys)

        for fname, fval in fields.items():
            self.assertEquals(fval, getattr(m, fname))

    @mock.patch("pulp_docker.plugins.models.Tag.objects")
    @mock.patch("pulp_docker.plugins.models.Tag.save")
    @mock.patch("pulp_docker.plugins.models.Tag._get_db")
    def test_tag_manifest__update_ignore_pulp_user_metadata(self, _get_db, _Tag_save, _Tag_objects):
        # Raise exception first, then succeed
        _Tag_save.side_effect = [models.mongoengine.NotUniqueError(), None]
        fields = dict(
            tag_name="aaa",
            repo_id="fedora",
            schema_version=42,
            manifest_type="blip",
            manifest_digest="sha256:123",
        )
        fields_old = dict(fields)
        # Change digest and pulp_user_metadata, they should be overwritten
        fields_old['manifest_digest'] = "sha13:1"
        fields_old['pulp_user_metadata'] = {'branch': 'master'}
        fields_old['name'] = fields_old.pop('tag_name')
        existing_tag = models.Tag(**fields_old)

        qs = models.TagQuerySet(existing_tag, None)
        _Tag_objects.get.return_value = existing_tag

        m = qs.tag_manifest(**fields)
        self.assertEquals(id(existing_tag), id(m))

        # tag_name corresponds to name
        fields['name'] = fields.pop('tag_name')

        unit_keys = dict((x, fields[x]) for x in existing_tag.unit_key_fields)
        _Tag_objects.get.assert_called_once_with(**unit_keys)

        # We should have preserved the old pulp_user_metadata
        fields['pulp_user_metadata'] = fields_old['pulp_user_metadata']
        for fname, fval in fields.items():
            self.assertEquals(fval, getattr(m, fname))
