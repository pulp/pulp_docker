import unittest

import mock
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.importer import Importer
from pulp.plugins.model import Repository

import data
from pulp_docker.common import constants
from pulp_docker.common.models import DockerImage
from pulp_docker.plugins.importers.importer import DockerImporter, entry_point
from pulp_docker.plugins.importers import upload


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


@mock.patch('pulp_docker.plugins.importers.sync.SyncStep')
@mock.patch('tempfile.mkdtemp', spec_set=True)
@mock.patch('shutil.rmtree')
class TestSyncRepo(unittest.TestCase):
    def setUp(self):
        super(TestSyncRepo, self).setUp()
        self.repo = Repository('repo1', working_dir='/a/b/c')
        self.sync_conduit = mock.MagicMock()
        self.config = mock.MagicMock()
        self.importer = DockerImporter()

    def test_calls_sync_step(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.assert_called_once_with(repo=self.repo, conduit=self.sync_conduit,
                                               config=self.config,
                                               working_dir=mock_mkdtemp.return_value)

    def test_calls_sync(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.return_value.sync.assert_called_once_with()

    def test_makes_temp_dir(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_mkdtemp.assert_called_once_with(dir=self.repo.working_dir)

    def test_removes_temp_dir(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_rmtree.assert_called_once_with(mock_mkdtemp.return_value, ignore_errors=True)

    def test_removes_temp_dir_after_exception(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        class MyError(Exception):
            pass
        mock_sync_step.return_value.sync.side_effect = MyError
        self.assertRaises(MyError, self.importer.sync_repo, self.repo,
                          self.sync_conduit, self.config)

        mock_rmtree.assert_called_once_with(mock_mkdtemp.return_value, ignore_errors=True)


@mock.patch.object(upload, 'update_tags', spec_set=True)
class TestUploadUnit(unittest.TestCase):
    def setUp(self):
        self.unit_key = {'image_id': data.busybox_ids[0]}
        self.repo = Repository('repo1')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_save_conduit(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        conduit = mock_save.call_args[0][0]

        self.assertTrue(conduit is self.conduit)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_models(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        models = mock_save.call_args[0][1]

        for model in models:
            self.assertTrue(isinstance(model, DockerImage))

        ids = [m.image_id for m in models]

        self.assertEqual(tuple(ids), data.busybox_ids)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_ancestry(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        ancestry = mock_save.call_args[0][2]

        self.assertEqual(tuple(ancestry), data.busybox_ids)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_filepath(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        path = mock_save.call_args[0][3]

        self.assertEqual(path, data.busybox_tar_path)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_added_tags(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        mock_update_tags.assert_called_once_with(self.repo.id, data.busybox_tar_path)


class TestImportUnits(unittest.TestCase):

    def setUp(self):
        self.unit_key = {'image_id': data.busybox_ids[0]}
        self.source_repo = Repository('repo_source')
        self.dest_repo = Repository('repo_dest')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})

    def test_import_all(self):
        mock_unit = mock.Mock(unit_key={'image_id': 'foo'}, metadata={})
        self.conduit.get_source_units.return_value = [mock_unit]
        result = DockerImporter().import_units(self.source_repo, self.dest_repo, self.conduit,
                                               self.config)
        self.assertEquals(result, [mock_unit])
        self.conduit.associate_unit.assert_called_once_with(mock_unit)

    def test_import_no_parent(self):
        mock_unit = mock.Mock(unit_key={'image_id': 'foo'}, metadata={})
        result = DockerImporter().import_units(self.source_repo, self.dest_repo, self.conduit,
                                               self.config, units=[mock_unit])
        self.assertEquals(result, [mock_unit])
        self.conduit.associate_unit.assert_called_once_with(mock_unit)

    def test_import_with_parent(self):
        mock_unit1 = mock.Mock(unit_key={'image_id': 'foo'}, metadata={'parent_id': 'bar'})
        mock_unit2 = mock.Mock(unit_key={'image_id': 'bar'}, metadata={})
        self.conduit.get_source_units.return_value = [mock_unit2]
        result = DockerImporter().import_units(self.source_repo, self.dest_repo, self.conduit,
                                               self.config, units=[mock_unit1])
        self.assertEquals(result, [mock_unit1, mock_unit2])
        calls = [mock.call(mock_unit1), mock.call(mock_unit2)]
        self.conduit.associate_unit.assert_has_calls(calls)


class TestValidateConfig(unittest.TestCase):
    def test_always_true(self):
        for repo, config in [['a', 'b'], [1, 2], [mock.Mock(), {}], ['abc', {'a': 2}]]:
            # make sure all attempts are validated
            self.assertEqual(DockerImporter().validate_config(repo, config), (True, ''))


class TestRemoveUnit(unittest.TestCase):

    def setUp(self):
        self.repo = Repository('repo_source')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})
        self.mock_unit = mock.Mock(unit_key={'image_id': 'foo'}, metadata={})

    @mock.patch('pulp_docker.plugins.importers.importer.manager_factory.repo_manager')
    def test_remove_with_tag(self, mock_repo_manager):
        mock_repo_manager.return_value.get_repo_scratchpad.return_value = \
            {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                        constants.IMAGE_ID_KEY: 'foo'}]}
        DockerImporter().remove_units(self.repo, [self.mock_unit], self.config)
        mock_repo_manager.return_value.set_repo_scratchpad.assert_called_once_with(
            self.repo.id, {u'tags': []}
        )

    @mock.patch('pulp_docker.plugins.importers.importer.manager_factory.repo_manager')
    def test_remove_without_tag(self, mock_repo_manager):
        expected_tags = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                    constants.IMAGE_ID_KEY: 'bar'}]}
        mock_repo_manager.return_value.get_repo_scratchpad.return_value = expected_tags

        DockerImporter().remove_units(self.repo, [self.mock_unit], self.config)
        mock_repo_manager.return_value.set_repo_scratchpad.assert_called_once_with(
            self.repo.id, expected_tags)
