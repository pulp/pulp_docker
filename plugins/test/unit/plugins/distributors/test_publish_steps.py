import os
import shutil
import tempfile
import unittest

from mock import Mock, patch

from pulp.devel.unit.util import touch
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository
from pulp.plugins.util.publish_step import PublishStep

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import publish_steps


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

    def test_process_units(self):
        step = publish_steps.PublishImagesStep()
        step.parent = self.parent
        step.redirect_context = Mock()
        file_list = ['ancestry', 'layer', 'json']
        for file_name in file_list:
            touch(os.path.join(self.content_directory, file_name))
        unit = Mock(unit_key={'image_id': 'foo_image'}, storage_path=self.content_directory)
        step.get_working_dir = Mock(return_value=self.publish_directory)
        step.process_unit(unit)
        step.redirect_context.add_unit_metadata.assert_called_once_with(unit)
        for file_name in file_list:
            self.assertTrue(os.path.exists(os.path.join(self.publish_directory, 'web',
                                                        'foo_image', file_name)))

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

    @patch('pulp_docker.plugins.distributors.publish_steps.AtomicDirectoryPublishStep')
    @patch('pulp_docker.plugins.distributors.publish_steps.PublishImagesStep')
    @patch('pulp_docker.plugins.distributors.publish_steps.WebPublisher.'
           'get_working_dir', return_value='export/dir')
    def test_init(self, get_working_dir, mock_images_step, mock_web_publish_step):
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }
        publisher = publish_steps.WebPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.children, [mock_images_step.return_value,
                                               mock_web_publish_step.return_value])


class TestExportPublisher(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.working_temp = os.path.join(self.working_directory, 'work')
        self.repo = Mock(id='foo', working_dir=self.working_temp)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_docker.plugins.distributors.publish_steps.ExportPublisher.'
           'get_working_dir', return_value='export/dir')
    def test_init(self, get_working_dir):
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }
        publisher = publish_steps.ExportPublisher(self.repo, mock_conduit, mock_config)
        self.assertTrue(isinstance(publisher.children[0], publish_steps.PublishImagesStep))
        self.assertTrue(isinstance(publisher.children[1], publish_steps.SaveTarFilePublishStep))
        tar_step = publisher.children[1]
        self.assertEquals(tar_step.source_dir, 'export/dir')
        self.assertEquals(tar_step.publish_file,
                          os.path.join(self.publish_dir, 'export/repo/foo.tar'))
