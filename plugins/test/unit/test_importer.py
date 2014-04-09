import unittest

import mock
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.importer import Importer
from pulp.plugins.model import Repository
from pulp.server.managers.repo.cud import RepoManager

import data
from pulp_docker.common import constants
from pulp_docker.common.models import DockerImage
from pulp_docker.plugins.importers.importer import DockerImporter, entry_point


class TestEntryPoint(unittest.TestCase):
    def test_returns_importer(self):
        importer, config = entry_point()

        self.assertTrue(issubclass(importer, Importer))

    def test_returns_config(self):
        importer, config = entry_point()

        # make sure it's at least the correct type
        self.assertTrue(isinstance(config, dict))


class TestBasics(unittest.TestCase):
    def test_metadata(self):
        metadata = DockerImporter.metadata()

        self.assertEqual(metadata['id'], constants.IMPORTER_TYPE_ID)
        self.assertEqual(metadata['types'], [constants.IMAGE_TYPE_ID])
        self.assertTrue(len(metadata['display_name']) > 0)


@mock.patch.object(RepoManager, 'update_repo_scratchpad', spec_set=True)
class TestUploadUnit(unittest.TestCase):
    def setUp(self):
        self.unit_key = {'image_id': data.busybox_ids[0]}
        self.repo = Repository('repo1')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_save_conduit(self, mock_save, mock_update):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        conduit = mock_save.call_args[0][0]

        self.assertTrue(conduit is self.conduit)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_models(self, mock_save, mock_update):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        models = mock_save.call_args[0][1]

        for model in models:
            self.assertTrue(isinstance(model, DockerImage))

        ids = [m.image_id for m in models]

        self.assertEqual(tuple(ids), data.busybox_ids)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_ancestry(self, mock_save, mock_update):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        ancestry = mock_save.call_args[0][2]

        self.assertEqual(tuple(ancestry), data.busybox_ids)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_filepath(self, mock_save, mock_update):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        path = mock_save.call_args[0][3]

        self.assertEqual(path, data.busybox_tar_path)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_added_tags(self, mock_save, mock_update):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        mock_update.assert_called_once_with(self.repo.id, {'tags': {'latest': data.busybox_ids[0]}})


class TestValidateConfig(unittest.TestCase):
    def test_always_true(self):
        for repo, config in [['a', 'b'], [1, 2], [mock.Mock(), {}], ['abc', {'a': 2}]]:
            # make sure all attempts are validated
            self.assertEqual(DockerImporter().validate_config(repo, config), (True, ''))
