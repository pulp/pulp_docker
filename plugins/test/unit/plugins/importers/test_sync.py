"""
This module contains tests for the pulp_docker.plugins.importers.sync module.
"""
import os
import shutil
import tempfile
import unittest
from gettext import gettext as _

import mock
from pulp.common.plugins import importer_constants
from pulp.plugins import config as plugin_config
from pulp.plugins.util import publish_step
from pulp.server import exceptions
from pulp.server.managers import factory

from pulp_docker.common import constants
from pulp_docker.plugins import models, registry
from pulp_docker.plugins.importers import sync


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')

factory.initialize()


class TestDownloadManifestsStep(unittest.TestCase):
    """
    This class contains tests for the DownloadManifestsStep class.
    """
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.__init__',
                side_effect=sync.publish_step.PluginStep.__init__, autospec=True)
    def test___init__(self, __init__):
        """
        Assert correct attributes and calls from __init__().
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()

        step = sync.DownloadManifestsStep(repo, conduit, config)

        self.assertEqual(step.description, _('Downloading manifests'))
        __init__.assert_called_once_with(
            step, step_type=constants.SYNC_STEP_METADATA, repo=repo, conduit=conduit, config=config,
            plugin_type=constants.IMPORTER_TYPE_ID)

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.process_main')
    def test_process_main_with_one_layer(self, super_process_main, from_json):
        """
        Test process_main() when there is only one layer.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()
        step.parent.index_repository.get_tags.return_value = ['latest']
        with open(os.path.join(TEST_DATA_PATH, 'manifest_one_layer.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        step.parent.index_repository.get_manifest.return_value = digest, manifest
        step.parent.available_manifests = []
        step.parent.available_blobs = []

        with mock.patch('__builtin__.open') as mock_open:
            step.process_main()

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        super_process_main.assert_called_once_with()
        step.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.index_repository.get_manifest.assert_called_once_with('latest')
        from_json.assert_called_once_with(manifest, digest)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.available_manifests), 1)
        self.assertEqual(step.parent.available_manifests[0].digest, digest)
        # There should be one layer
        expected_blob_sum = ('sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6'
                             'ef')
        expected_layer = step.parent.available_manifests[0].fs_layers[0]
        self.assertEqual(expected_layer.blob_sum, expected_blob_sum)
        self.assertEqual(step.parent.available_manifests[0].fs_layers, [expected_layer])
        # A blob with the correct digest should have been added to the parent.available_blobs
        # list
        expected_blob = step.parent.available_blobs[0]
        self.assertEqual(expected_blob.digest, expected_blob_sum)
        self.assertEqual(step.parent.available_blobs, [expected_blob])

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.process_main')
    def test_process_main_with_repeated_layers(self, super_process_main, from_json):
        """
        Test process_main() when the various tags contains some layers in common, which is a
        typical pattern. The available_blobs set on the SyncStep should only have the layers once
        each so that we don't try to download them more than once.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()
        step.parent.index_repository.get_tags.return_value = ['latest']
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        step.parent.index_repository.get_manifest.return_value = digest, manifest
        step.parent.available_manifests = []
        step.parent.available_blobs = []

        with mock.patch('__builtin__.open') as mock_open:
            step.process_main()

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        super_process_main.assert_called_once_with()
        step.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.index_repository.get_manifest.assert_called_once_with('latest')
        from_json.assert_called_once_with(manifest, digest)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.available_manifests), 1)
        self.assertEqual(step.parent.available_manifests[0].digest, digest)
        # There should be two layers, but oddly one of them is used three times
        expected_blob_sums = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        expected_digests = [expected_blob_sums[i] for i in (0, 0, 1, 0)]
        layer_digests = [layer.blob_sum for layer in step.parent.available_manifests[0].fs_layers]
        self.assertEqual(layer_digests, expected_digests)
        # The layers should have been added to the parent.available_blobs list, in no
        # particular order
        self.assertEqual(set([u.digest for u in step.parent.available_blobs]),
                         set(expected_blob_sums))

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.process_main')
    def test_process_main_with_unique_layers(self, super_process_main, from_json):
        """
        Test process_main() when the various tags all have unique layers.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()
        step.parent.index_repository.get_tags.return_value = ['latest']
        with open(os.path.join(TEST_DATA_PATH, 'manifest_unique_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        step.parent.index_repository.get_manifest.return_value = digest, manifest
        step.parent.available_manifests = []
        step.parent.available_blobs = []

        with mock.patch('__builtin__.open') as mock_open:
            step.process_main()

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        super_process_main.assert_called_once_with()
        step.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.index_repository.get_manifest.assert_called_once_with('latest')
        from_json.assert_called_once_with(manifest, digest)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.available_manifests), 1)
        self.assertEqual(step.parent.available_manifests[0].digest, digest)
        # There should be two layers, but oddly one of them is used three times
        expected_blob_sums = [
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11',
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef']
        fs_layer_blob_sums = [
            layer.blob_sum for layer in step.parent.available_manifests[0].fs_layers]
        self.assertEqual(fs_layer_blob_sums, expected_blob_sums)
        # The layers should have been added to the parent.available_blobs list, in no
        # particular order
        self.assertEqual(set([u.digest for u in step.parent.available_blobs]),
                         set(expected_blob_sums))


class TestSaveUnitsStep(unittest.TestCase):
    """
    This class contains tests for the SaveUnitsStep class.
    """
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.__init__',
                side_effect=sync.publish_step.PluginStep.__init__, autospec=True)
    def test___init__(self, super___init__):
        """
        Assert the correct operation of the __init__() method.
        """
        step = sync.SaveUnitsStep()

        super___init__.assert_called_once_with(step, step_type=constants.SYNC_STEP_SAVE)
        self.assertEqual(step.description, _('Saving Manifests and Blobs'))

    @mock.patch('pulp_docker.plugins.importers.sync.repository.associate_single_unit')
    def test_process_main_new_blobs(self, associate_single_unit):
        """
        Test process_main() when there are new Blobs that were downloaded.
        """
        step = sync.SaveUnitsStep()
        digests = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        step.parent = mock.MagicMock()
        step.parent.get_working_dir.return_value = '/some/path'
        step.parent.get_repo.return_value = mock.MagicMock()
        step.parent.step_get_local_manifests.units_to_download = []
        step.parent.step_get_local_blobs.units_to_download = [
            models.Blob(digest=digest) for digest in digests]
        units = list(step.get_iterator())

        for unit in units:
            unit.import_content = mock.MagicMock()
            unit.save = mock.MagicMock()

            step.process_main(item=unit)

            unit.import_content.assert_called_once_with(os.path.join('/some/path', unit.digest))
            unit.save.assert_called_once_with()
            self.assertEqual(associate_single_unit.mock_calls[-1][1][0],
                             step.parent.get_repo.return_value)
            self.assertEqual(associate_single_unit.mock_calls[-1][1][1], unit)

    @mock.patch('pulp_docker.plugins.importers.sync.repository.associate_single_unit')
    def test_process_main_new_blobs_and_manifests(self, associate_single_unit):
        """
        Test process_main() when there are new Blobs and one Manifest that were downloaded.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep()
        # Simulate two newly downloaded blobs
        blob_digests = (
            'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
            'sha256:cc8567d70002e957612902a8e985ea129d831ebe04057d88fb644857caa45d11')
        step.parent = mock.MagicMock()
        step.parent.get_working_dir.return_value = working_dir
        step.parent.get_repo.return_value = mock.MagicMock()
        step.parent.step_get_local_blobs.units_to_download = [
            models.Blob(digest=digest) for digest in blob_digests]
        # Simulate one newly downloaded manifest
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        manifest_digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        manifest = models.Manifest.from_json(manifest, manifest_digest)
        step.parent.step_get_local_metadata.units_to_download = [manifest]
        units = list(step.get_iterator())

        for unit in units:
            unit.import_content = mock.MagicMock()
            unit.save = mock.MagicMock()

            step.process_main(item=unit)

            unit.import_content.assert_called_once_with(os.path.join(working_dir, unit.digest))
            unit.save.assert_called_once_with()
            self.assertEqual(associate_single_unit.mock_calls[-1][1][0],
                             step.parent.get_repo.return_value)
            self.assertEqual(associate_single_unit.mock_calls[-1][1][1], unit)

    @mock.patch('pulp_docker.plugins.importers.sync.repository.associate_single_unit')
    def test_process_main_new_manifests(self, associate_single_unit):
        """
        Test process_main() when there are new manifests that were downloaded.
        """
        working_dir = '/working/dir/'
        step = sync.SaveUnitsStep()
        step.parent = mock.MagicMock()
        step.parent.get_working_dir.return_value = working_dir
        step.parent.get_repo.return_value = mock.MagicMock()
        step.parent.step_get_local_blobs.units_to_download = []
        # Simulate one newly downloaded manifest
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        manifest_digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        manifest = models.Manifest.from_json(manifest, manifest_digest)
        step.parent.step_get_local_metadata.units_to_download = [manifest]
        units = list(step.get_iterator())

        for unit in units:
            unit.import_content = mock.MagicMock()
            unit.save = mock.MagicMock()

            step.process_main(item=unit)

            unit.import_content.assert_called_once_with(os.path.join(working_dir, unit.digest))
            unit.save.assert_called_once_with()
            self.assertEqual(associate_single_unit.mock_calls[-1][1][0],
                             step.parent.get_repo.return_value)
            self.assertEqual(associate_single_unit.mock_calls[-1][1][1], unit)


class TestSyncStep(unittest.TestCase):
    """
    This class contains tests for the SyncStep class.
    """
    def setUp(self):
        """
        Set up a temporary directory.
        """
        self.working_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check')
    def test___init___with_v2_registry(self, api_version_check, _validate, _working_directory_path):
        """
        Test the __init__() method when the V2Repository does not raise a NotImplementedError with
        the api_version_check() method, indicating that the feed URL is a Docker v2 registry.
        """
        _working_directory_path.return_value = self.working_dir
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})

        step = sync.SyncStep(repo=repo, conduit=conduit, config=config)

        self.assertEqual(step.description, _('Syncing Docker Repository'))
        # The config should get validated
        _validate.assert_called_once_with(config)
        # available_blobs should have been initialized to an empty list
        self.assertEqual(step.available_blobs, [])
        self.assertEqual(step.available_manifests, [])
        # Ensure that the index_repository was initialized correctly
        self.assertEqual(type(step.index_repository), registry.V2Repository)
        self.assertEqual(step.index_repository.name, 'busybox')
        self.assertEqual(step.index_repository.download_config.max_concurrent, 25)
        self.assertEqual(step.index_repository.registry_url, 'https://registry.example.com')
        self.assertEqual(step.index_repository.working_dir, self.working_dir)
        # The version check should have happened, and since we mocked it, it will not raise an error
        api_version_check.assert_called_once_with()
        # The correct children should be in place in the right order
        self.assertEqual(
            [type(child) for child in step.children],
            [sync.DownloadManifestsStep, publish_step.GetLocalUnitsStep,
             publish_step.GetLocalUnitsStep, publish_step.DownloadStep, sync.SaveUnitsStep])
        # Ensure the first step was initialized correctly
        self.assertEqual(step.children[0].repo, repo)
        self.assertEqual(step.children[0].conduit, conduit)
        self.assertEqual(step.children[0].config, config)
        # And the second step
        self.assertTrue(step.children[1] is step.step_get_local_manifests)
        self.assertEqual(step.children[1].plugin_type, constants.IMPORTER_TYPE_ID)
        self.assertEqual(step.children[1].available_units, step.available_manifests)
        # And the third step
        self.assertTrue(step.children[2] is step.step_get_local_blobs)
        self.assertEqual(step.children[2].plugin_type, constants.IMPORTER_TYPE_ID)
        self.assertEqual(step.children[2].available_units, step.available_blobs)
        # And the fourth
        self.assertEqual(step.children[3].step_type, constants.SYNC_STEP_DOWNLOAD)
        self.assertEqual(step.children[3].repo, repo)
        self.assertEqual(step.children[3].config, config)
        self.assertEqual(step.children[3].description, _('Downloading remote files'))

    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    def test___init___without_v2_registry(self, _validate, _working_directory_path):
        """
        Test the __init__() method when the V2Repository raises a NotImplementedError with the
        api_version_check() method, indicating that the feed URL is not a Docker v2 registry.
        """
        _working_directory_path.return_value = self.working_dir
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        # This feed does not implement a registry, so it will raise the NotImplementedError
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})

        self.assertRaises(NotImplementedError, sync.SyncStep, repo, conduit, config)

        # The config should get validated
        _validate.assert_called_once_with(config)

    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', mock.MagicMock())
    def test_generate_download_requests(self, _working_directory_path):
        """
        Assert correct operation of the generate_download_requests() method.
        """
        _working_directory_path.return_value = self.working_dir
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = plugin_config.PluginCallConfiguration(
            {},
            {'feed': 'https://registry.example.com', 'upstream_name': 'busybox',
             importer_constants.KEY_MAX_DOWNLOADS: 25})
        step = sync.SyncStep(repo, conduit, config)
        step.step_get_local_blobs.units_to_download = [
            models.Blob(digest=i) for i in ['cool', 'stuff']]

        requests = step.generate_download_requests()

        requests = list(requests)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].url, 'https://registry.example.com/v2/busybox/blobs/cool')
        self.assertEqual(requests[0].destination, os.path.join(self.working_dir, 'cool'))
        self.assertEqual(requests[0].data, None)
        self.assertEqual(requests[0].headers, None)
        self.assertEqual(requests[1].url, 'https://registry.example.com/v2/busybox/blobs/stuff')
        self.assertEqual(requests[1].destination, os.path.join(self.working_dir, 'stuff'))
        self.assertEqual(requests[1].data, None)
        self.assertEqual(requests[1].headers, None)

    def test_required_settings(self):
        """
        Assert that the required_settings class attribute is set correctly.
        """
        self.assertEqual(sync.SyncStep.required_settings,
                         (constants.CONFIG_KEY_UPSTREAM_NAME, importer_constants.KEY_FEED))

    def test__validate_missing_one_key(self):
        """
        Test the _validate() method when one required config key is missing.
        """
        config = plugin_config.PluginCallConfiguration(
            {}, {'upstream_name': 'busybox', importer_constants.KEY_MAX_DOWNLOADS: 25})

        try:
            sync.SyncStep._validate(config)
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
            sync.SyncStep._validate(config)
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
        sync.SyncStep._validate(config)
