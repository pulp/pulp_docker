import os
import shutil
import tarfile
import tempfile
import time
import unittest

from mock import Mock, patch
from pulp.devel.unit.util import touch
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository
from pulp.plugins.util.publish_step import BasePublisher

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import publish_steps


class TestAtomicDirectoryPublishStep(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main_alternate_id(self):
        step = publish_steps.AtomicDirectoryPublishStep('foo', 'bar', 'baz', step_id='alternate')
        self.assertEquals(step.step_id, 'alternate')

    def test_process_main_default_id(self):
        step = publish_steps.AtomicDirectoryPublishStep('foo', 'bar', 'baz')
        self.assertEquals(step.step_id, constants.PUBLISH_STEP_DIRECTORY)

    def test_process_main(self):
        source_dir = os.path.join(self.working_directory, 'source')
        master_dir = os.path.join(self.working_directory, 'master')
        publish_dir = os.path.join(self.working_directory, 'publish', 'bar')
        publish_dir += '/'
        step = publish_steps.AtomicDirectoryPublishStep(source_dir,
                                                        [('/', publish_dir)], master_dir)
        step.parent = Mock(timestamp=str(time.time()))

        # create some files to test
        sub_file = os.path.join(source_dir, 'foo', 'bar.html')
        touch(sub_file)

        # Create an old directory to test
        old_dir = os.path.join(master_dir, 'foo')
        os.makedirs(old_dir)
        step.process_main()

        target_file = os.path.join(publish_dir, 'foo', 'bar.html')
        self.assertEquals(True, os.path.exists(target_file))
        self.assertEquals(1, len(os.listdir(master_dir)))

    def test_process_main_multiple_targets(self):
        source_dir = os.path.join(self.working_directory, 'source')
        master_dir = os.path.join(self.working_directory, 'master')
        publish_dir = os.path.join(self.working_directory, 'publish', 'bar')
        publish_dir += '/'
        # create some files to test
        sub_file = os.path.join(source_dir, 'foo', 'bar.html')
        touch(sub_file)
        sub_file = os.path.join(source_dir, 'qux', 'quux.html')
        touch(sub_file)

        target_qux = os.path.join(self.working_directory, 'publish', 'qux.html')

        step = publish_steps.AtomicDirectoryPublishStep(source_dir,
                                                        [('/', publish_dir),
                                                         ('qux/quux.html', target_qux)
                                                         ], master_dir)
        step.parent = Mock(timestamp=str(time.time()))

        step.process_main()

        target_file = os.path.join(publish_dir, 'foo', 'bar.html')
        self.assertEquals(True, os.path.exists(target_file))
        self.assertEquals(True, os.path.exists(target_qux))


class TestPublishImagesStep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.working_directory = os.path.join(self.temp_dir, 'working')
        self.publish_directory = os.path.join(self.temp_dir, 'publish')
        self.content_directory = os.path.join(self.temp_dir, 'content')
        os.makedirs(self.working_directory)
        os.makedirs(self.publish_directory)
        os.makedirs(self.content_directory)
        repo = Repository('foo_repo_id', working_dir=self.working_directory)
        config = PluginCallConfiguration(None, None)
        conduit = RepoPublishConduit(repo.id, 'foo_repo')
        conduit.get_repo_scratchpad = Mock(return_value={u'tags': {}})
        self.parent = BasePublisher(repo, conduit, config)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

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


class TestSaveTarFilePublishStep(unittest.TestCase):
    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_process_main(self):
        source_dir = os.path.join(self.working_directory, 'source')
        os.makedirs(source_dir)
        target_file = os.path.join(self.working_directory, 'target', 'target.tar')
        step = publish_steps.SaveTarFilePublishStep(source_dir, target_file)

        touch(os.path.join(source_dir, 'foo.txt'))
        step.process_main()

        with tarfile.open(target_file) as tar_file:
            names = tar_file.getnames()
            self.assertEquals(names, ['', 'foo.txt'])


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
    def test_init(self, mock_images_step, mock_web_publish_step):
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }
        publisher = publish_steps.WebPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.process_steps, [mock_images_step.return_value])
        self.assertEquals(publisher.post_metadata_process_steps,
                          [mock_web_publish_step.return_value])


class TestExportPublisher(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.working_temp = os.path.join(self.working_directory, 'work')
        self.repo = Mock(id='foo', working_dir=self.working_temp)

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_docker.plugins.distributors.publish_steps.SaveTarFilePublishStep')
    @patch('pulp_docker.plugins.distributors.publish_steps.PublishImagesStep')
    def test_init(self, mock_images_step, mock_tar_file_step):
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }
        publisher = publish_steps.ExportPublisher(self.repo, mock_conduit, mock_config)
        self.assertEquals(publisher.process_steps, [mock_images_step.return_value])
        self.assertEquals(publisher.post_metadata_process_steps,
                          [mock_tar_file_step.return_value])
