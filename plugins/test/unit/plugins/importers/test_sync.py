"""
This module contains tests for the pulp_docker.plugins.importers.sync module.
"""
import os
import unittest
from gettext import gettext as _

import mock
from pulp.common.plugins import importer_constants
from pulp.plugins import config as plugin_config, model
from pulp.server import exceptions
from pulp.server.managers import factory

from pulp_docker.common import constants, models
from pulp_docker.plugins import registry
from pulp_docker.plugins.importers import sync


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')

factory.initialize()


class TestDownloadManifestsStep(unittest.TestCase):
    """
    This class contains tests for the DownloadManifestsStep class.
    """
    @mock.patch('pulp_docker.plugins.importers.sync.PluginStep.__init__',
                side_effect=sync.PluginStep.__init__, autospec=True)
    def test___init__(self, __init__):
        """
        Assert correct attributes and calls from __init__().
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = '/some/path'

        step = sync.DownloadManifestsStep(repo, conduit, config, working_dir)

        self.assertEqual(step.description, _('Downloading manifests'))
        __init__.assert_called_once_with(step, constants.SYNC_STEP_METADATA, repo, conduit, config,
                                         working_dir, constants.IMPORTER_TYPE_ID)

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.PluginStep.process_main')
    def test_process_main_with_one_layer(self, super_process_main, from_json):
        """
        Test process_main() when there is only one layer.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = '/some/path'
        step = sync.DownloadManifestsStep(repo, conduit, config, working_dir)
        step.parent = mock.MagicMock()
        step.parent.parent.index_repository.get_tags.return_value = ['latest']
        with open(os.path.join(TEST_DATA_PATH, 'manifest_one_layer.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        step.parent.parent.available_units = []
        step.parent.parent.index_repository.get_manifest.return_value = digest, manifest
        step.parent.manifests = {}

        with mock.patch('__builtin__.open') as mock_open:
            step.process_main()

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        super_process_main.assert_called_once_with()
        step.parent.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.parent.index_repository.get_manifest.assert_called_once_with('latest')
        from_json.assert_called_once_with(manifest, digest)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.manifests), 1)
        self.assertEqual(step.parent.manifests[digest].digest, digest)
        # There should be one layer
        expected_blob_sum = ('sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6'
                             'ef')
        self.assertEqual(
            step.parent.manifests[digest].fs_layers,
            [{"blobSum": expected_blob_sum}]
        )
        # The layer should have been added to the parent.parent.available_units list
        self.assertEqual(step.parent.parent.available_units, [{'digest': expected_blob_sum}])

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.PluginStep.process_main')
    def test_process_main_with_repeated_layers(self, super_process_main, from_json):
        """
        Test process_main() when the various tags contains some layers in common, which is a
        typical pattern. The available_units set on the V2SyncStep should only have the layers once
        each so that we don't try to download them more than once.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = '/some/path'
        step = sync.DownloadManifestsStep(repo, conduit, config, working_dir)
        step.parent = mock.MagicMock()
        step.parent.parent.index_repository.get_tags.return_value = ['latest']
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        step.parent.parent.available_units = []
        step.parent.parent.index_repository.get_manifest.return_value = digest, manifest
        step.parent.manifests = {}

        with mock.patch('__builtin__.open') as mock_open:
            step.process_main()

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        super_process_main.assert_called_once_with()
        step.parent.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.parent.index_repository.get_manifest.assert_called_once_with('latest')
        from_json.assert_called_once_with(manifest, digest)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.manifests), 1)
        self.assertEqual(step.parent.manifests[digest].digest, digest)
        # There should be two layers, but oddly one of them is used three times
        expected_blob_sums = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        expected_fs_layers = [{'blobSum': expected_blob_sums[i]} for i in (0, 0, 1, 0)]
        self.assertEqual(step.parent.manifests[digest].fs_layers, expected_fs_layers)
        # The layers should have been added to the parent.parent.available_units list, in no
        # particular order
        self.assertEqual(set([u['digest'] for u in step.parent.parent.available_units]),
                         set(expected_blob_sums))

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.PluginStep.process_main')
    def test_process_main_with_unique_layers(self, super_process_main, from_json):
        """
        Test process_main() when the various tags all have unique layers.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = '/some/path'
        step = sync.DownloadManifestsStep(repo, conduit, config, working_dir)
        step.parent = mock.MagicMock()
        step.parent.parent.index_repository.get_tags.return_value = ['latest']
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        step.parent.parent.available_units = []
        step.parent.parent.index_repository.get_manifest.return_value = digest, manifest
        step.parent.manifests = {}

        with mock.patch('__builtin__.open') as mock_open:
            step.process_main()

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        super_process_main.assert_called_once_with()
        step.parent.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.parent.index_repository.get_manifest.assert_called_once_with('latest')
        from_json.assert_called_once_with(manifest, digest)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.manifests), 1)
        self.assertEqual(step.parent.manifests[digest].digest, digest)
        # There should be two layers, but oddly one of them is used three times
        expected_blob_sums = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        expected_fs_layers = [{'blobSum': expected_blob_sums[i]} for i in (0, 0, 1, 0)]
        self.assertEqual(step.parent.manifests[digest].fs_layers, expected_fs_layers)
        # The layers should have been added to the parent.parent.available_units list, in no
        # particular order
        self.assertEqual(set([u['digest'] for u in step.parent.parent.available_units]),
                         set(expected_blob_sums))


class TestGetLocalBlobsStep(unittest.TestCase):
    """
    This class contains tests for the GetLocalBlobsStep class.
    """
    def test__dict_to_unit(self):
        """
        Assert correct behavior from the _dict_to_unit() method.
        """
        step = sync.GetLocalBlobsStep(constants.IMPORTER_TYPE_ID, models.Blob.TYPE_ID,
                                      ['digest'], '/working/dir')
        step.conduit = mock.MagicMock()

        unit = step._dict_to_unit({'digest': 'abc123'})

        self.assertTrue(unit is step.conduit.init_unit.return_value)
        step.conduit.init_unit.assert_called_once_with(
            models.Blob.TYPE_ID, {'digest': 'abc123'}, {}, 'abc123')


class TestGetLocalManifestsStep(unittest.TestCase):
    """
    This class contains tests for the GetLocalManifestsStep class.
    """
    def test__dict_to_unit(self):
        """
        Assert correct behavior from the _dict_to_unit() method.
        """
        step = sync.GetLocalManifestsStep(constants.IMPORTER_TYPE_ID, models.Manifest.TYPE_ID,
                                          ['digest'], '/working/dir')
        step.conduit = mock.MagicMock()
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        manifest = models.Manifest.from_json(manifest, digest)
        step.parent = mock.MagicMock()
        step.parent.parent.step_get_metadata.manifests = {digest: manifest}

        unit = step._dict_to_unit({'digest': digest})

        self.assertTrue(unit is step.conduit.init_unit.return_value)
        step.conduit.init_unit.assert_called_once_with(
            manifest.TYPE_ID, manifest.unit_key, manifest.metadata, manifest.relative_path)


class TestGetMetadataStep(unittest.TestCase):
    """
    This class contains tests for the GetMetadataStep class.
    """
    @mock.patch('pulp_docker.plugins.importers.sync.DownloadManifestsStep.__init__',
                return_value=None)
    @mock.patch('pulp_docker.plugins.importers.sync.GetLocalManifestsStep.__init__',
                return_value=None)
    def test___init__(self, get_local_manifests_step___init__, download_manifests_step___init__):
        """
        Assert that __init__() establishes the correct attributes and child tasks.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = '/some/path'

        step = sync.GetMetadataStep(repo, conduit, config, working_dir)

        self.assertEqual(step.description, _('Retrieving metadata'))
        self.assertEqual(step.manifests, {})
        # Make sure the children are set up
        self.assertEqual(len(step.children), 2)
        self.assertEqual(type(step.children[0]), sync.DownloadManifestsStep)
        self.assertEqual(type(step.children[1]), sync.GetLocalManifestsStep)
        self.assertEqual(step.children[1], step.step_get_local_units)
        download_manifests_step___init__.assert_called_once_with(repo, conduit, config, working_dir)
        get_local_manifests_step___init__.assert_called_once_with(
            constants.IMPORTER_TYPE_ID, models.Manifest.TYPE_ID, ['digest'], working_dir)

    def test_available_units(self):
        """
        Assert correct operation from the available_units property.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        working_dir = '/some/path'
        step = sync.GetMetadataStep(repo, conduit, config, working_dir)
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        manifest = models.Manifest.from_json(manifest, digest)
        step.manifests = {digest: manifest}

        self.assertEqual(step.available_units, [{'digest': digest}])


class TestSaveUnitsStep(unittest.TestCase):
    """
    This class contains tests for the SaveUnitsStep class.
    """
    @mock.patch('pulp_docker.plugins.importers.sync.PluginStep.__init__',
                side_effect=sync.PluginStep.__init__, autospec=True)
    def test___init__(self, super___init__):
        """
        Assert the correct operation of the __init__() method.
        """
        working_dir = '/working/dir/'

        step = sync.SaveUnitsStep(working_dir)

        super___init__.assert_called_once_with(
            step, step_type=constants.SYNC_STEP_SAVE, plugin_type=constants.IMPORTER_TYPE_ID,
            working_dir=working_dir)
        self.assertEqual(step.description, _('Saving manifests and blobs'))

    @mock.patch('pulp_docker.plugins.importers.sync.shutil.move')
    def test__move_files_with_blob(self, move):
        """
        Assert correct operation from the _move_files() method with a Blob unit.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep(working_dir)
        unit_key = {'digest': 'some_digest'}
        metadata = {}
        storage_path = '/a/cool/storage/path'
        unit = model.Unit(models.Blob.TYPE_ID, unit_key, metadata, storage_path)

        step._move_file(unit)

        move.assert_called_once_with('/working/dir/some_digest', storage_path)

    @mock.patch('pulp_docker.plugins.importers.sync.shutil.move')
    def test__move_files_with_manifest(self, move):
        """
        Assert correct operation from the _move_files() method with a Manifest unit.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep(working_dir)
        unit_key = {'digest': 'some_digest'}
        metadata = {'some': 'metadata'}
        storage_path = '/a/cool/storage/path'
        unit = model.Unit(models.Manifest.TYPE_ID, unit_key, metadata, storage_path)

        step._move_file(unit)

        move.assert_called_once_with('/working/dir/some_digest', storage_path)

    @mock.patch('pulp_docker.plugins.importers.sync.SaveUnitsStep._move_file')
    def test_process_main_new_blobs(self, _move_file):
        """
        Test process_main() when there are new Blobs that were downloaded.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep(working_dir)
        digests = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        step.parent = mock.MagicMock()
        step.parent.step_get_local_units.units_to_download = [
            {'digest': digest} for digest in digests]

        def fake_init_unit(type_id, unit_key, metadata, path):
            """
            Return the two units for the two blobs for two invocations of init_unit.
            """
            return model.Unit(type_id, unit_key, metadata, path)

        step.parent.get_conduit.return_value.init_unit.side_effect = fake_init_unit

        step.process_main()

        # Both units should have been moved
        self.assertEqual(_move_file.call_count, 2)
        self.assertEqual([call[1][0].unit_key['digest'] for call in _move_file.mock_calls],
                         [d for d in digests])
        # Both units should have been saved
        self.assertEqual(step.parent.get_conduit.return_value.save_unit.call_count, 2)
        self.assertEqual(
            [call[1][0].unit_key['digest'] for call in
             step.parent.get_conduit.return_value.save_unit.mock_calls],
            [d for d in digests])

    @mock.patch('pulp_docker.plugins.importers.sync.SaveUnitsStep._move_file')
    def test_process_main_new_blobs_and_manifests(self, _move_file):
        """
        Test process_main() when there are new Blobs and manifests that were downloaded.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep(working_dir)
        # Simulate two newly downloaded blobs
        blob_digests = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        step.parent = mock.MagicMock()
        step.parent.step_get_local_units.units_to_download = [
            {'digest': digest} for digest in blob_digests]
        # Simulate one newly downloaded manifest
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        manifest_digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        manifest = models.Manifest.from_json(manifest, manifest_digest)
        step.parent.step_get_metadata.manifests = {manifest_digest: manifest}
        step.parent.step_get_metadata.step_get_local_units.units_to_download = [
            {'digest': manifest_digest}]

        def fake_init_unit(type_id, unit_key, metadata, path):
            """
            Return the Unit for the invocation of init_unit.
            """
            return model.Unit(type_id, unit_key, metadata, path)

        step.parent.get_conduit.return_value.init_unit.side_effect = fake_init_unit

        step.process_main()

        # All three units should have been moved
        self.assertEqual(_move_file.call_count, 3)
        self.assertEqual(_move_file.mock_calls[0][1][0].unit_key, {'digest': manifest_digest})
        self.assertEqual([call[1][0].unit_key for call in _move_file.mock_calls[1:3]],
                         [{'digest': d} for d in blob_digests])
        # All three units should have been saved
        self.assertEqual(step.parent.get_conduit.return_value.save_unit.call_count, 3)
        self.assertEqual(
            step.parent.get_conduit.return_value.save_unit.mock_calls[0][1][0].unit_key,
            {'digest': manifest_digest})
        self.assertEqual(
            [call[1][0].unit_key['digest'] for call in
                step.parent.get_conduit.return_value.save_unit.mock_calls[1:3]],
            [d for d in blob_digests])
        # The Units' metadata should have been initialized properly
        self.assertEqual(
            step.parent.get_conduit.return_value.save_unit.mock_calls[0][1][0].metadata['name'],
            'hello-world')

    @mock.patch('pulp_docker.plugins.importers.sync.SaveUnitsStep._move_file')
    def test_process_main_new_manifests(self, _move_file):
        """
        Test process_main() when there are new manifests that were downloaded.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep(working_dir)
        step.parent = mock.MagicMock()
        # Simulate 0 new blobs
        step.parent.step_get_local_units.units_to_download = []
        # Simulate one newly downloaded manifest
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        manifest = models.Manifest.from_json(manifest, digest)
        step.parent.step_get_metadata.manifests = {digest: manifest}
        step.parent.step_get_metadata.step_get_local_units.units_to_download = [{'digest': digest}]

        def fake_init_unit(type_id, unit_key, metadata, path):
            """
            Return the Unit for the invocation of init_unit.
            """
            return model.Unit(type_id, unit_key, metadata, path)

        step.parent.get_conduit.return_value.init_unit.side_effect = fake_init_unit

        step.process_main()

        # The new manifest should have been moved
        self.assertEqual(_move_file.call_count, 1)
        self.assertEqual(_move_file.mock_calls[0][1][0].unit_key, {'digest': digest})
        # The manifest should have been saved
        self.assertEqual(step.parent.get_conduit.return_value.save_unit.call_count, 1)
        self.assertEqual(
            step.parent.get_conduit.return_value.save_unit.mock_calls[0][1][0].unit_key,
            {'digest': digest})
        # The Manifest's metadata should have been initialized properly
        self.assertEqual(
            step.parent.get_conduit.return_value.save_unit.mock_calls[0][1][0].metadata['name'],
            'hello-world')

    @mock.patch('pulp_docker.plugins.importers.sync.SaveUnitsStep._move_file')
    def test_process_main_no_units(self, _move_file):
        """
        When there are no units that were new to download nothing should happen.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep(working_dir)
        step.parent = mock.MagicMock()
        # Simulate 0 new blobs
        step.parent.step_get_local_units.units_to_download = []
        # Simulate 0 new manifests
        step.parent.step_get_metadata.manifests = {}
        step.parent.step_get_metadata.step_get_local_units.units_to_download = []

        step.process_main()

        # Nothing should have been moved
        self.assertEqual(_move_file.call_count, 0)
        # Nothing should have been saved
        self.assertEqual(step.parent.get_conduit.return_value.save_unit.call_count, 0)


class TestV2SyncStep(unittest.TestCase):
    """
    This class contains tests for the V2SyncStep class.
    """
    @mock.patch('pulp_docker.plugins.importers.sync.V2SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check')
    def test___init___with_v2_registry(self, api_version_check, _validate):
        """
        Test the __init__() method when the V2Repository does not raise a NotImplementedError with
        the api_version_check() method, indicating that the feed URL is a Docker v2 registry.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})
        working_dir = '/some/path'

        step = sync.V2SyncStep(repo, conduit, config, working_dir)

        self.assertEqual(step.description, _('Syncing Docker Repository'))
        # The config should get validated
        _validate.assert_called_once_with(config)
        # available_units should have been initialized to an empty list
        self.assertEqual(step.available_units, [])
        # Ensure that the index_repository was initialized correctly
        self.assertEqual(type(step.index_repository), registry.V2Repository)
        self.assertEqual(step.index_repository.name, 'busybox')
        self.assertEqual(step.index_repository.download_config.max_concurrent, 25)
        self.assertEqual(step.index_repository.registry_url, 'https://registry.example.com')
        self.assertEqual(step.index_repository.working_dir, working_dir)
        # The version check should have happened, and since we mocked it, it will not raise an error
        api_version_check.assert_called_once_with()
        # The correct children should be in place in the right order
        self.assertEqual(
            [type(child) for child in step.children],
            [sync.GetMetadataStep, sync.GetLocalBlobsStep, sync.DownloadStep, sync.SaveUnitsStep])
        # Ensure the first step was initialized correctly
        self.assertEqual(step.children[0].repo, repo)
        self.assertEqual(step.children[0].conduit, conduit)
        self.assertEqual(step.children[0].config, config)
        self.assertEqual(step.children[0].working_dir, working_dir)
        # And the second step
        self.assertEqual(step.children[1].plugin_type, constants.IMPORTER_TYPE_ID)
        self.assertEqual(step.children[1].unit_type, models.Blob.TYPE_ID)
        self.assertEqual(step.children[1].unit_key_fields, ['digest'])
        self.assertEqual(step.children[1].working_dir, working_dir)
        # And the third step
        self.assertEqual(step.children[2].step_type, constants.SYNC_STEP_DOWNLOAD)
        self.assertEqual(step.children[2].repo, repo)
        self.assertEqual(step.children[2].config, config)
        self.assertEqual(step.children[2].working_dir, working_dir)
        self.assertEqual(step.children[2].description, _('Downloading remote files'))
        # And the final step
        self.assertEqual(step.children[3].working_dir, working_dir)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', mock.MagicMock())
    def test_generate_download_requests(self):
        """
        Assert correct operation of the generate_download_requests() method.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})
        working_dir = '/some/path'
        step = sync.V2SyncStep(repo, conduit, config, working_dir)
        step.step_get_local_units.units_to_download = [
            {'digest': i} for i in ['cool', 'stuff']]

        requests = step.generate_download_requests()

        requests = list(requests)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].url, 'https://registry.example.com/v2/busybox/blobs/cool')
        self.assertEqual(requests[0].destination, '/some/path/cool')
        self.assertEqual(requests[0].data, None)
        self.assertEqual(requests[0].headers, None)
        self.assertEqual(requests[1].url, 'https://registry.example.com/v2/busybox/blobs/stuff')
        self.assertEqual(requests[1].destination, '/some/path/stuff')
        self.assertEqual(requests[1].data, None)
        self.assertEqual(requests[1].headers, None)

    def test_required_settings(self):
        """
        Assert that the required_settings class attribute is set correctly.
        """
        self.assertEqual(sync.V2SyncStep.required_settings,
                         (constants.CONFIG_KEY_UPSTREAM_NAME, importer_constants.KEY_FEED))

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', mock.MagicMock())
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._build_final_report')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.process_lifecycle')
    def test_sync(self, process_lifecycle, _build_final_report):
        """
        Assert correct operation of the sync() method.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})
        working_dir = '/some/path'
        step = sync.SyncStep(repo, conduit, config, working_dir)

        step.sync()

        process_lifecycle.assert_called_once_with()
        _build_final_report.assert_called_once_with()

    def test__validate_missing_one_key(self):
        """
        Test the _validate() method when one required config key is missing.
        """
        config = plugin_config.PluginCallConfiguration(
            {}, {'upstream_name': 'busybox', importer_constants.KEY_MAX_DOWNLOADS: 25})

        try:
            sync.V2SyncStep._validate(config)
            self.fail('An Exception should have been raised, but was not!')
        except exceptions.MissingValue as e:
            self.assertEqual(e.property_names, ['feed'])

    def test__validate_missing_two_keys(self):
        """
        Test the _validate() method when two required config keys are missing.
        """
        config = plugin_config.PluginCallConfiguration(
            {}, {importer_constants.KEY_MAX_DOWNLOADS: 25})

        try:
            sync.V2SyncStep._validate(config)
            self.fail('An Exception should have been raised, but was not!')
        except exceptions.MissingValue as e:
            self.assertEqual(set(e.property_names), set(['upstream_name', 'feed']))

    def test__validate_success_case(self):
        """
        Assert that _validate() returns sucessfully when all required config keys are present.
        """
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})

        # This should not raise an Exception
        sync.V2SyncStep._validate(config)
