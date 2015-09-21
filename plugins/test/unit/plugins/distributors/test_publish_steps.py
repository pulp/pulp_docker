import os
import shutil
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest


from mock import Mock, patch

from pulp.devel.unit.util import touch
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.util.publish_step import PublishStep
from pulp.server.db.models import Repository

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import publish_steps
from pulp_docker.plugins.db import models


class TestPublishImagesStep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = os.path.join(self.temp_dir, 'working')
        self.publish_directory = os.path.join(self.temp_dir, 'publish')
        self.content_directory = os.path.join(self.temp_dir, 'content')
        os.makedirs(self.working_directory)
        os.makedirs(self.publish_directory)
        os.makedirs(self.content_directory)
        repo = Repository('foo_repo_id')
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={u'tags': {}})
        self.parent = PublishStep('test-step', repo, conduit, config,
                                  working_dir=self.working_directory)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch('pulp_docker.plugins.distributors.publish_steps.RedirectFileContext')
    def test_initialize_metdata(self, mock_context):
        step = publish_steps.PublishImagesStep()
        step.parent = self.parent
        step.initialize()
        mock_context.return_value.initialize.assert_called_once_with()

    def test_process_main(self):
        step = publish_steps.PublishImagesStep()
        step.parent = self.parent
        step.redirect_context = Mock()
        file_list = ['ancestry', 'layer', 'json']
        for file_name in file_list:
            touch(os.path.join(self.content_directory, file_name))
        unit = models.DockerImage(image_id='foo_image', storage_path=self.content_directory)
        step.get_working_dir = Mock(return_value=self.publish_directory)
        step.process_main(item=unit)
        step.redirect_context.add_unit_metadata.assert_called_once_with(unit)
        for file_name in file_list:
            self.assertTrue(os.path.exists(os.path.join(self.publish_directory, 'web',
                                                        'foo_image', file_name)))

    def test_get_count(self):
        """
        Test getting the unit count if there are images in the repo
        """
        step = publish_steps.PublishImagesStep()
        step.repo = Repository(content_unit_counts={constants.IMAGE_TYPE_ID: 3})
        self.assertEquals(3, step.get_total())

    def test_get_count_empty(self):
        """
        Test getting the unit count if there are no images in the repo
        """
        step = publish_steps.PublishImagesStep()
        step.repo = Repository(content_unit_counts={})

        self.assertEquals(0, step.get_total())

    @patch('pulp_docker.plugins.distributors.publish_steps.repo_controller.find_repo_content_units')
    def test_get_iterator(self, m_find_units):
        step = publish_steps.PublishImagesStep()
        step.repo = 'foo'
        unit = models.DockerImage(image_id='abc123', size=2)
        m_find_units.return_value = [unit]

        result = list(step.get_iterator())

        self.assertEquals(m_find_units.call_args[0][0], step.repo)
        actual_query = m_find_units.call_args[1]['repo_content_unit_q'].to_query(models.DockerImage)
        expected_query = {'_content_type_id': constants.IMAGE_TYPE_ID}
        self.assertDictEqual(actual_query, expected_query)
        self.assertListEqual(result, [unit])

    def test_finalize(self):
        step = publish_steps.PublishImagesStep()
        step.redirect_context = Mock()
        step.finalize()
        step.redirect_context.finalize.assert_called_once_with()


class TestWebPublisher(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.master_dir = os.path.join(self.working_directory, 'master')
        self.working_temp = os.path.join(self.working_directory, 'work')
        self.repo = Mock(id='foo', working_dir=self.working_temp)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_docker.plugins.distributors.publish_steps.WebPublisher.'
           'get_working_dir', return_value='export/dir')
    @patch('pulp_docker.plugins.distributors.publish_steps.AtomicDirectoryPublishStep')
    @patch('pulp_docker.plugins.distributors.publish_steps.PublishImagesStep')
    def test_init(self, mock_images_step, mock_web_publish_step, m_get_working_dir):
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }
        publisher = publish_steps.WebPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.children, [mock_images_step.return_value,
                                               mock_web_publish_step.return_value])


class TestExportPublisher(unittest.TestCase):

    @patch('pulp_docker.plugins.distributors.publish_steps.ExportPublisher.'
           'get_working_dir', return_value='export/dir')
    def test_init(self, m_get_working_dir):
        repo = Repository(repo_id='foo')
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: 'publish/dir'
        }
        publisher = publish_steps.ExportPublisher(repo, mock_conduit, mock_config)
        self.assertTrue(isinstance(publisher.children[0], publish_steps.PublishImagesStep))
        self.assertTrue(isinstance(publisher.children[1], publish_steps.SaveTarFilePublishStep))
        tar_step = publisher.children[1]
        self.assertEquals(tar_step.source_dir, 'export/dir')
        self.assertEquals(tar_step.publish_file,
                          os.path.join('publish/dir', 'export/repo/foo.tar'))
