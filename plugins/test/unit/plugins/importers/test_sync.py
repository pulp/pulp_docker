"""
This module contains tests for the pulp_docker.plugins.importers.sync module.
"""
import inspect
import os
import shutil
import tempfile
from gettext import gettext as _

import mock
from nectar.request import DownloadRequest
from pulp.common.plugins import importer_constants
from pulp.common.compat import unittest
from pulp.plugins import config as plugin_config
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.util import publish_step
from pulp.server import exceptions
from pulp.server.exceptions import MissingValue, PulpCodedException
from pulp.server.managers import factory

from pulp_docker.common import constants, error_codes
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
    def test_process_manifest_with_one_layer(self, from_json):
        """
        Test _process_manifest() when there is only one layer.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()

        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()

        with open(os.path.join(TEST_DATA_PATH, 'manifest_one_layer.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        repo_tag = 'latest'
        repo_upstream_name = 'busybox'
        step.parent.available_manifests = []

        with mock.patch('__builtin__.open') as mock_open:
            step._process_manifest(manifest, digest, repo_tag, repo_upstream_name, set())

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        from_json.assert_called_once_with(manifest, digest, repo_tag, repo_upstream_name)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.available_manifests), 1)
        self.assertEqual(step.parent.available_manifests[0].digest, digest)
        # There should be one layer
        expected_blob_sum = ('sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6'
                             'ef')
        expected_layer = step.parent.available_manifests[0].fs_layers[0]
        self.assertEqual(expected_layer.blob_sum, expected_blob_sum)
        self.assertEqual(step.parent.available_manifests[0].fs_layers, [expected_layer])

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    def test_process_manifest_schema2_with_one_layer(self, from_json):
        """
        Test _process_manifest() when there is only one layer.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()

        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()

        with open(os.path.join(TEST_DATA_PATH, 'manifest_schema2_one_layer.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:817a12c32a39bbe394944ba49de563e085f1d3c5266eb8e9723256bc4448680e'
        repo_tag = 'latest'
        repo_upstream_name = 'busybox'
        step.parent.available_manifests = []

        with mock.patch('__builtin__.open') as mock_open:
            step._process_manifest(manifest, digest, repo_tag, repo_upstream_name, set())

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        from_json.assert_called_once_with(manifest, digest, repo_tag, repo_upstream_name)
        # There should be one manifest that has the correct digest
        self.assertEqual(len(step.parent.available_manifests), 1)
        self.assertEqual(step.parent.available_manifests[0].digest, digest)
        # There should be one layer
        expected_blob_sum = ('sha256:4b0bc1c4050b03c95ef2a8e36e25feac42fd31283e8c30b3ee5df6b043155d'
                             '3c')
        expected_layer = step.parent.available_manifests[0].fs_layers[0]
        self.assertEqual(expected_layer.blob_sum, expected_blob_sum)
        self.assertEqual(step.parent.available_manifests[0].fs_layers, [expected_layer])

    @mock.patch('pulp_docker.plugins.importers.sync.DownloadManifestsStep._process_manifest')
    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.process_main')
    def test_process_main_with_one_layer(self, super_process_main, from_json, mock_manifest):
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
        manifest = models.Manifest.from_json(manifest, digest, 'latest', 'busybox')
        step.parent.index_repository.get_manifest.return_value = [(digest, manifest)]
        step.parent.available_blobs = []

        step.process_main()

        super_process_main.assert_called_once_with()
        step.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.index_repository.get_manifest.assert_called_once_with('latest')
        # since it is a manifest schema 1 version, there should no config_layer
        self.assertFalse(manifest.config_layer)

    @mock.patch('pulp_docker.plugins.importers.sync.DownloadManifestsStep._process_manifest')
    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    @mock.patch('pulp_docker.plugins.importers.sync.publish_step.PluginStep.process_main')
    def test_process_main_schema2_with_one_layer(self, super_process_main, from_json,
                                                 mock_manifest):
        """
        Test process_main() when there is only one layer.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()

        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()
        step.parent.index_repository.get_tags.return_value = ['latest']

        with open(os.path.join(TEST_DATA_PATH, 'manifest_schema2_one_layer.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:817a12c32a39bbe394944ba49de563e085f1d3c5266eb8e9723256bc4448680e'
        manifest = models.Manifest.from_json(manifest, digest, 'latest', 'busybox')
        step.parent.index_repository.get_manifest.return_value = [(digest, manifest)]
        step.parent.available_blobs = []

        step.process_main()

        super_process_main.assert_called_once_with()
        step.parent.index_repository.get_tags.assert_called_once_with()
        step.parent.index_repository.get_manifest.assert_called_once_with('latest')
        # since it is a manifest schema 2 version, there should a config_layer
        self.assertTrue(manifest.config_layer)

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    def test_process_manifest_with_repeated_layers(self, from_json):
        """
        Test _process_manifest() when the various tags contains some layers in common, which is a
        typical pattern. The available_blobs set on the SyncStep should only have the layers once
        each so that we don't try to download them more than once.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()

        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()

        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        repo_tag = 'latest'
        repo_upstream_name = 'busybox'
        step.parent.available_manifests = []

        with mock.patch('__builtin__.open') as mock_open:
            step._process_manifest(manifest, digest, repo_tag, repo_upstream_name, set())

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        from_json.assert_called_once_with(manifest, digest, repo_tag, repo_upstream_name)
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

    @mock.patch('pulp_docker.plugins.importers.sync.models.Manifest.from_json',
                side_effect=models.Manifest.from_json)
    def test_process_manifest_with_unique_layers(self, from_json):
        """
        Test _process_manifest() when the various tags all have unique layers.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        config = mock.MagicMock()

        step = sync.DownloadManifestsStep(repo, conduit, config)
        step.parent = mock.MagicMock()

        with open(os.path.join(TEST_DATA_PATH, 'manifest_unique_layers.json')) as manifest_file:
            manifest = manifest_file.read()
        digest = 'sha256:a001e892f3ba0685184486b08cda99bf81f551513f4b56e72954a1d4404195b1'
        repo_tag = 'latest'
        repo_upstream_name = 'busybox'
        step.parent.available_manifests = []

        with mock.patch('__builtin__.open') as mock_open:
            step._process_manifest(manifest, digest, repo_tag, repo_upstream_name, set())

            # Assert that the manifest was written to disk in the working dir
            mock_open.return_value.__enter__.return_value.write.assert_called_once_with(manifest)

        from_json.assert_called_once_with(manifest, digest, repo_tag, repo_upstream_name)
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
            unit.save_and_import_content = mock.MagicMock()

            step.process_main(item=unit)
            path = os.path.join('/some/path', unit.digest)
            unit.save_and_import_content.assert_called_once_with(path)
            self.assertEqual(associate_single_unit.mock_calls[-1][1][0],
                             step.parent.get_repo.return_value.repo_obj)
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
        tag = 'latest'
        upstream_name = 'synctest'
        manifest = models.Manifest.from_json(manifest, manifest_digest, tag, upstream_name)
        step.parent.step_get_local_metadata.units_to_download = [manifest]
        units = list(step.get_iterator())

        for unit in units:
            unit.save_and_import_content = mock.MagicMock()

            step.process_main(item=unit)
            path = os.path.join(working_dir, unit.digest)
            unit.save_and_import_content.assert_called_once_with(path)
            self.assertEqual(associate_single_unit.mock_calls[-1][1][0],
                             step.parent.get_repo.return_value.repo_obj)
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
        tag = 'latest'
        upstream_name = 'synctest'
        manifest = models.Manifest.from_json(manifest, manifest_digest, tag, upstream_name)
        step.parent.step_get_local_metadata.units_to_download = [manifest]
        units = list(step.get_iterator())

        for unit in units:
            unit.save_and_import_content = mock.MagicMock()

            step.process_main(item=unit)

            path = os.path.join(working_dir, unit.digest)
            unit.save_and_import_content.assert_called_once_with(path)
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
        plugin_config = {
            constants.CONFIG_KEY_UPSTREAM_NAME: 'pulp/crane',
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)
        self.repo = mock.MagicMock(repo_id='repo1')
        self.conduit = mock.MagicMock()

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=True)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=False)
    def test___init___with_v2_registry(self, v1_api_check, api_version_check, _validate,
                                       _working_directory_path):
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
             publish_step.GetLocalUnitsStep, sync.TokenAuthDownloadStep, sync.SaveUnitsStep,
             sync.SaveTagsStep])
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
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    def test_init_v1(self, mock_check_v1, mock_check_v2, mock_validate, _working_directory_path):
        _working_directory_path.return_value = self.working_dir
        # re-run this with the mock in place
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)

        self.assertEqual(step.step_id, constants.SYNC_STEP_MAIN)

        # make sure the children are present
        step_ids = set([child.step_id for child in step.children])
        self.assertTrue(constants.SYNC_STEP_METADATA_V1 in step_ids)
        self.assertTrue(constants.SYNC_STEP_GET_LOCAL_V1 in step_ids)
        self.assertTrue(constants.SYNC_STEP_DOWNLOAD_V1 in step_ids)
        self.assertTrue(constants.SYNC_STEP_SAVE_V1 in step_ids)

        # make sure it instantiated a Repository object
        self.assertTrue(isinstance(step.v1_index_repository, registry.V1Repository))
        self.assertEqual(step.v1_index_repository.name, 'pulp/crane')
        self.assertEqual(step.v1_index_repository.registry_url, 'http://pulpproject.org/')

        # these are important because child steps will populate them with data
        self.assertEqual(step.v1_available_units, [])
        self.assertEqual(step.v1_tags, {})

        mock_validate.assert_called_once_with(self.config)

    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    def test___init___without_v2_registry(self, mock_v2_check, mock_v1_check,
                                          _validate, _working_directory_path):
        """
        Test the __init__() method when the V2Repository raises a NotImplementedError with the
        api_version_check() method, indicating that the feed URL is not a Docker v2 registry.
        """
        _working_directory_path.return_value = self.working_dir
        repo = mock.MagicMock()
        conduit = mock.MagicMock()

        with self.assertRaises(PulpCodedException) as error:
            sync.SyncStep(repo, conduit, self.config)
        self.assertEqual(error.exception.error_code, error_codes.DKR1008)

        # The config should get validated
        _validate.assert_called_once_with(self.config)

    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check')
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check')
    def test___init__nothing_enabled(self, v1_check, v2_check, validate, working_dir_path):
        """
        Test when both v1 and v2 are disabled, PulpCodedException is raised.
        """
        working_dir_path.return_value = self.working_dir
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = False
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V2] = False

        with self.assertRaises(PulpCodedException) as error:
            sync.SyncStep(repo, conduit, self.config)

        validate.assert_called_once_with(self.config)
        self.assertEqual(error.exception.error_code, error_codes.DKR1008)
        self.assertFalse(v1_check.called)
        self.assertFalse(v2_check.called)

    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.add_v1_steps')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.add_v2_steps')
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=True)
    def test___init___only_v1_enabled(
            self,
            v2_check,
            v1_check,
            validate,
            working_dir_path,
            add_v2_steps,
            add_v1_steps):
        """
        Test only v1 enabled.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        working_dir_path.return_value = self.working_dir
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V2] = False

        sync.SyncStep(repo, conduit, self.config)

        validate.assert_called_once_with(self.config)
        add_v1_steps.assert_called_once_with(repo, self.config)
        v1_check.assert_called_once_with()
        self.assertFalse(v2_check.called)
        self.assertFalse(add_v2_steps.called)

    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.add_v1_steps')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.add_v2_steps')
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=True)
    def test___init___only_v2_enabled(
            self,
            v2_check,
            v1_check,
            validate,
            working_dir_path,
            add_v2_steps,
            add_v1_steps):
        """
        Test only v2 enabled.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        working_dir_path.return_value = self.working_dir
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = False
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V2] = True

        sync.SyncStep(repo, conduit, self.config)

        validate.assert_called_once_with(self.config)
        add_v2_steps.assert_called_once_with(repo, conduit, self.config)
        v2_check.assert_called_once_with()
        self.assertFalse(v1_check.called)
        self.assertFalse(add_v1_steps.called)

    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.add_v1_steps')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep.add_v2_steps')
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep._validate')
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=True)
    def test___init___v1_and_v2_enabled(
            self,
            v2_check,
            v1_check,
            validate,
            working_dir_path,
            add_v2_steps,
            add_v1_steps):
        """
        Test both v1 and v2 enabled.
        """
        repo = mock.MagicMock()
        conduit = mock.MagicMock()
        working_dir_path.return_value = self.working_dir
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V2] = True

        sync.SyncStep(repo, conduit, self.config)

        validate.assert_called_once_with(self.config)
        add_v1_steps.assert_called_once_with(repo, self.config)
        add_v2_steps.assert_called_once_with(repo, conduit, self.config)
        v1_check.assert_called_once_with()
        v2_check.assert_called_once_with()

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

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_v1_generate_download_requests(self, mock_working_dir, mock_v1_check, mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)
        step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))

        try:
            generator = step.v1_generate_download_requests()
            self.assertTrue(inspect.isgenerator(generator))

            download_reqs = list(generator)

            self.assertEqual(len(download_reqs), 3)
            for req in download_reqs:
                self.assertTrue(isinstance(req, DownloadRequest))
        finally:
            shutil.rmtree(step.working_dir)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_generate_download_requests_correct_urls(self, mock_working_dir, mock_v1_check,
                                                     mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)
        step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))

        try:
            generator = step.v1_generate_download_requests()

            # make sure the urls are correct
            urls = [req.url for req in generator]
            self.assertTrue('http://pulpproject.org/v1/images/image1/ancestry' in urls)
            self.assertTrue('http://pulpproject.org/v1/images/image1/json' in urls)
            self.assertTrue('http://pulpproject.org/v1/images/image1/layer' in urls)
        finally:
            shutil.rmtree(step.working_dir)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_generate_download_requests_correct_destinations(self, mock_working_dir,
                                                             mock_v1_check, mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)
        step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))

        try:
            generator = step.v1_generate_download_requests()

            # make sure the urls are correct
            destinations = [req.destination for req in generator]
            self.assertTrue(os.path.join(step.working_dir, 'image1', 'ancestry')
                            in destinations)
            self.assertTrue(os.path.join(step.working_dir, 'image1', 'json')
                            in destinations)
            self.assertTrue(os.path.join(step.working_dir, 'image1', 'layer')
                            in destinations)
        finally:
            shutil.rmtree(step.working_dir)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_generate_download_reqs_creates_dir(self, mock_working_dir, mock_v1_check,
                                                mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)
        step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))

        try:
            list(step.v1_generate_download_requests())

            # make sure it created the destination directory
            self.assertTrue(os.path.isdir(os.path.join(step.working_dir, 'image1')))
        finally:
            shutil.rmtree(step.working_dir)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_generate_download_reqs_existing_dir(self, mock_working_dir, mock_v1_check,
                                                 mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)
        step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))
        os.makedirs(os.path.join(step.working_dir, 'image1'))

        try:
            # just make sure this doesn't complain
            list(step.v1_generate_download_requests())
        finally:
            shutil.rmtree(step.working_dir)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_generate_download_reqs_perm_denied(self, mock_working_dir, mock_v1_check,
                                                mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        try:
            step = sync.SyncStep(self.repo, self.conduit, self.config)
            step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))
            step.working_dir = '/not/allowed'

            # make sure the permission denies OSError bubbles up
            self.assertRaises(OSError, list, step.v1_generate_download_requests())
        finally:
            shutil.rmtree(mock_working_dir.return_value)

    @mock.patch('pulp_docker.plugins.registry.V2Repository.api_version_check', return_value=False)
    @mock.patch('pulp_docker.plugins.registry.V1Repository.api_version_check', return_value=True)
    @mock.patch('pulp.server.managers.repo._common._working_directory_path')
    def test_generate_download_reqs_ancestry_exists(self, mock_working_dir, mock_v1_check,
                                                    mock_v2_check):
        mock_working_dir.return_value = tempfile.mkdtemp()
        self.config.override_config[constants.CONFIG_KEY_ENABLE_V1] = True
        step = sync.SyncStep(self.repo, self.conduit, self.config)
        step.v1_step_get_local_units.units_to_download.append(models.Image(image_id='image1'))
        os.makedirs(os.path.join(step.working_dir, 'image1'))
        # simulate the ancestry file already existing
        open(os.path.join(step.working_dir, 'image1/ancestry'), 'w').close()

        try:
            # there should only be 2 reqs instead of 3, since the ancestry file already exists
            reqs = list(step.v1_generate_download_requests())
            self.assertEqual(len(reqs), 2)
        finally:
            shutil.rmtree(step.working_dir)

    def test_required_settings(self):
        """
        Assert that the required_settings class attribute is set correctly.
        """
        self.assertEqual(sync.SyncStep.required_settings,
                         (constants.CONFIG_KEY_UPSTREAM_NAME, importer_constants.KEY_FEED))

    def test_validate_pass(self):
        sync.SyncStep._validate(self.config)

    def test_validate_no_name_or_feed(self):
        config = PluginCallConfiguration({}, {})

        try:
            sync.SyncStep._validate(config)
        except MissingValue as e:
            self.assertTrue(importer_constants.KEY_FEED in e.property_names)
            self.assertTrue(constants.CONFIG_KEY_UPSTREAM_NAME in e.property_names)
        else:
            raise AssertionError('validation should have failed')

    def test_validate_no_name(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_FEED: 'http://foo'})

        try:
            sync.SyncStep._validate(config)
        except MissingValue, e:
            self.assertTrue(constants.CONFIG_KEY_UPSTREAM_NAME in e.property_names)
            self.assertEqual(len(e.property_names), 1)
        else:
            raise AssertionError('validation should have failed')

    def test_validate_no_feed(self):
        config = PluginCallConfiguration({}, {constants.CONFIG_KEY_UPSTREAM_NAME: 'centos'})

        try:
            sync.SyncStep._validate(config)
        except MissingValue, e:
            self.assertTrue(importer_constants.KEY_FEED in e.property_names)
            self.assertEqual(len(e.property_names), 1)
        else:
            raise AssertionError('validation should have failed')

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
