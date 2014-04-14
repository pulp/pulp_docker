import os
import shutil
import tempfile
import time
import unittest

from mock import Mock, patch
from pulp.devel.unit.util import touch

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
        step = publish_steps.AtomicDirectoryPublishStep(source_dir, publish_dir, master_dir)
        step.parent = Mock(timestamp=str(time.time()))

        # create some files to test
        sub_file = os.path.join(source_dir, 'foo', 'bar.html')
        touch(sub_file)

        step.process_main()

        target_file = os.path.join(publish_dir, 'foo', 'bar.html')
        self.assertEquals(True, os.path.exists(target_file))


class TestPublishImagesStep(unittest.TestCase):
    def setUp(self):
        self.working_directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    @patch('pulp_docker.plugins.distributors.publish_steps.ImagesFileContext')
    def test_initialize_metdata(self, mock_context):
        step = publish_steps.PublishImagesStep()
        step.parent = Mock()
        step.initialize()
        mock_context.return_value.initialize.assert_called_once_with()

    def test_process_units(self):
        step = publish_steps.PublishImagesStep()
        step.parent = Mock()
        step.context = Mock()
        step.process_unit('foo')
        step.context.add_unit_metadata.asser_called_once_with('foo')

    def test_finalize(self):
        step = publish_steps.PublishImagesStep()
        step.context = Mock()
        step.finalize()
        step.context.finalize.assert_called_once_with()


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
