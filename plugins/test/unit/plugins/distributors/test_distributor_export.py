import os
import shutil
import tempfile
import unittest

from mock import Mock, MagicMock, patch
from pulp.devel.unit.util import touch
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.distributor import Distributor
from pulp.server.db.models import Repository

from pulp_docker.common import constants
from pulp_docker.plugins.distributors.distributor_export import DockerExportDistributor, entry_point


class TestEntryPoint(unittest.TestCase):
    def test_returns_importer(self):
        distributor, config = entry_point()

        self.assertTrue(issubclass(distributor, Distributor))

    def test_returns_config(self):
        distributor, config = entry_point()

        # make sure it's at least the correct type
        self.assertTrue(isinstance(config, dict))


@patch('pulp_docker.plugins.distributors.distributor_web.models.Repository.objects')
class TestBasics(unittest.TestCase):

    def setUp(self):
        self.distributor = DockerExportDistributor()
        self.working_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_dir, ignore_errors=True)

    def test_metadata(self, m_repo_objects):
        metadata = DockerExportDistributor.metadata()

        self.assertEqual(metadata['id'], constants.DISTRIBUTOR_EXPORT_TYPE_ID)
        self.assertEqual(metadata['types'], [constants.IMAGE_TYPE_ID])
        self.assertTrue(len(metadata['display_name']) > 0)

    @patch('pulp_docker.plugins.distributors.distributor_export.configuration.validate_config')
    def test_validate_config(self, mock_validate, m_repo_objects):
        m_repo_objects.get_repo_or_missing_resource.return_value = Mock(repo_id='bar')
        repo = Mock()
        value = self.distributor.validate_config(repo, 'foo', Mock())
        mock_validate.assert_called_once_with(
            'foo', m_repo_objects.get_repo_or_missing_resource.return_value)
        self.assertEquals(value, mock_validate.return_value)

    @patch('pulp_docker.plugins.distributors.distributor_export.configuration.'
           'get_export_repo_directory')
    def test_distributor_removed(self, mock_repo_dir, m_repo_objects,):
        m_repo_objects.get_repo_or_missing_resource.return_value = Mock(repo_id='bar')
        mock_repo_dir.return_value = os.path.join(self.working_dir, 'repo')
        os.makedirs(mock_repo_dir.return_value)
        repo = Mock(id='bar')
        config = {}
        touch(os.path.join(mock_repo_dir.return_value, 'bar.tar'))
        self.distributor.distributor_removed(repo, config)

        self.assertEquals(0, len(os.listdir(mock_repo_dir.return_value)))

    @patch('pulp_docker.plugins.distributors.distributor_export.configuration.'
           'get_export_repo_directory')
    def test_distributor_removed_files_missing(self, mock_repo_dir, m_repo_objects):
        m_repo_objects.get.return_value = Repository(repo_id='bar')
        mock_repo_dir.return_value = os.path.join(self.working_dir, 'repo')
        os.makedirs(mock_repo_dir.return_value)
        repo = Mock(id='bar')
        config = {}
        self.distributor.distributor_removed(repo, config)

        self.assertEquals(0, len(os.listdir(mock_repo_dir.return_value)))

    @patch('pulp_docker.plugins.distributors.distributor_export.ExportPublisher')
    def test_publish_repo(self, mock_publisher, m_repo_objects):
        repo = Repository('test')
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(repo.id, 'foo_repo')
        self.distributor.publish_repo(repo, conduit, config)

        mock_publisher.return_value.process_lifecycle.assert_called_once_with()

    def test_cancel_publish_repo(self, m_repo_objects):
        self.distributor._publisher = MagicMock()
        self.distributor.cancel_publish_repo()
        self.assertTrue(self.distributor.canceled)

        self.distributor._publisher.cancel.assert_called_once_with()
