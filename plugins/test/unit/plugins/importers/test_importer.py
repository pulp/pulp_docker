import unittest

import mock
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.importer import Importer
from pulp.server.db.models import Repository

import data
from pulp_docker.common import constants
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


class TestSyncRepo(unittest.TestCase):

    @mock.patch('pulp_docker.plugins.importers.importer.sync.SyncStep')
    @mock.patch('pulp_docker.plugins.importers.importer.models.Repository.objects')
    def test_calls_process_lifecycle(self, m_repo_objects, mock_sync_step):
        repo = mock.Mock(id='repo1')
        sync_conduit = mock.MagicMock()
        config = mock.MagicMock()
        importer = DockerImporter()
        repo_instance = Repository()
        m_repo_objects.get_repo_or_missing_resource.return_value = repo_instance

        importer.sync_repo(repo, sync_conduit, config)

        mock_sync_step.assert_called_once_with(repo=repo_instance,
                                               conduit=sync_conduit,
                                               config=config)
        mock_sync_step.return_value.process_lifecycle.assert_called_once_with()


class TestCancel(unittest.TestCase):
    def setUp(self):
        super(TestCancel, self).setUp()
        self.importer = DockerImporter()

    def test_calls_cancel(self):
        self.importer.sync_step = mock.MagicMock()

        self.importer.cancel_sync_repo()

        # make sure the step's cancel method was called
        self.importer.sync_step.cancel.assert_called_once_with()


class TestUploadUnit(unittest.TestCase):

    @mock.patch('pulp_docker.plugins.importers.importer.upload.UploadStep')
    @mock.patch('pulp_docker.plugins.importers.importer.models.Repository.objects')
    def test_calls_process_lifecycle(self, m_repo_objects, m_step):
        repo = mock.Mock(id='repo1')
        conduit = mock.MagicMock()
        config = mock.MagicMock()
        importer = DockerImporter()
        repo_instance = Repository()
        m_repo_objects.get_repo_or_missing_resource.return_value = repo_instance

        importer.upload_unit(repo, constants.IMAGE_TYPE_ID, {}, {}, 'foo/path', conduit, config)
        m_step.assert_called_once_with(repo=repo_instance,
                                       file_path='foo/path',
                                       config=config)
        m_step.return_value.process_lifecycle.assert_called_once_with()


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


@mock.patch('pulp_docker.plugins.importers.importer.models.Repository.objects')
class TestRemoveUnit(unittest.TestCase):

    def setUp(self):
        self.repo = Repository('repo_source')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})
        self.mock_unit = mock.Mock(unit_key={'image_id': 'foo'}, metadata={})

    def test_remove_with_tag(self, mock_repo_qs):
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.scratchpad = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                constants.IMAGE_ID_KEY: 'foo'}]}
        DockerImporter().remove_units(self.repo, [self.mock_unit], self.config)
        self.assertEqual(mock_repo.scratchpad['tags'], [])

    def test_remove_without_tag(self, mock_repo_qs):
        expected_tags = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                    constants.IMAGE_ID_KEY: 'bar'}]}
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.scratchpad = expected_tags

        DockerImporter().remove_units(self.repo, [self.mock_unit], self.config)
        self.assertEqual(mock_repo.scratchpad['tags'], expected_tags['tags'])
