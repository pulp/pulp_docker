import os
import shutil
import tempfile
import unittest
import time

from mock import Mock, patch

from pulp.plugins.util import publish_step

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import publish_steps


class StepAdapter(object):
    """Adapter allowing use of arbitrary callable as a publish step."""
    def __init__(self, callable):
        self._callable = callable

    def process(self):
        self._callable()

    def get_progress_report(self):
        return {}

    @property
    def children(self):
        return []


class TestV2WebPublisher(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.master_dir = os.path.join(self.working_directory, 'master')
        self.working_temp = os.path.join(self.working_directory, 'work')
        self.repo = Mock(id='foo', working_dir=self.working_temp)

        v2_dir = os.path.join(self.publish_dir, 'v2')
        self.app_file = os.path.join(v2_dir, 'app', 'foo.json')
        self.tags_file = os.path.join(v2_dir, 'web', 'foo', 'tags', 'list')

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def mock_no_units(self, publisher):
        """Adjust all steps on a publisher such that all UnitModelPluginSteps
        will process 0 units (simulating an empty repository)."""
        for step in publisher.children:
            if isinstance(step, publish_step.UnitModelPluginStep):
                step._total = 0
                step.get_iterator = lambda: iter([])

    def make_empty_publisher(self):
        """Returns a V2WebPublisher mocked for publishing an empty repo."""
        mock_conduit = Mock()
        mock_config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }
        publisher = publish_steps.V2WebPublisher(self.repo, mock_conduit, mock_config)
        self.mock_no_units(publisher)
        return publisher

    @patch('selinux.restorecon')
    @patch('pulp_docker.plugins.distributors.publish_steps.V2WebPublisher.'
           'get_working_dir')
    def test_publish_empty(self, get_working_dir, restorecon):
        """Publishing an empty repository generates tag list and redirect file at expected paths"""
        get_working_dir.return_value = self.working_temp
        publisher = self.make_empty_publisher()

        # Precondition: output files don't exist prior to publish
        self.assertFalse(os.path.exists(self.app_file))
        self.assertFalse(os.path.exists(self.tags_file))

        # Publish an empty repo
        publisher.process_lifecycle()

        # Postcondition: the app and tag files exist
        # (it is beyond the scope of this test to verify their content)
        self.assertTrue(os.path.exists(self.app_file))
        self.assertTrue(os.path.exists(self.tags_file))

    @patch('selinux.restorecon')
    @patch('pulp_docker.plugins.distributors.publish_steps.V2WebPublisher.'
           'get_working_dir')
    def test_publish_is_atomic(self, get_working_dir, restorecon):
        """During republish, old tag list and redirect file is reachable"""
        get_working_dir.return_value = self.working_temp

        # Initial publish
        self.make_empty_publisher().process_lifecycle()

        # Output files should exist
        self.assertTrue(os.path.exists(self.app_file))
        self.assertTrue(os.path.exists(self.tags_file))

        # Get the real paths (symlinks resolved) so we can compare later
        # to see if the files have been redirected
        old_app_file = os.path.realpath(self.app_file)
        old_tags_file = os.path.realpath(self.tags_file)

        # Ensure next publish gets a different timestamp
        time.sleep(0.05)

        invariant_checks = []

        def invariant():
            # This invariant must hold at each step during the publish:
            # app/tags files should still point at the old files
            self.assertEqual(old_app_file, os.path.realpath(self.app_file))
            self.assertEqual(old_tags_file, os.path.realpath(self.tags_file))
            invariant_checks.append(True)

        publisher = self.make_empty_publisher()
        for step in publisher.children:
            # Check the invariant prior to each step
            step.add_child(StepAdapter(invariant))

        publisher.process_lifecycle()

        # Verify that we did check the invariant at each step
        self.assertEquals(len(invariant_checks), len(publisher.children))

        # Output files should still exist
        self.assertTrue(os.path.exists(self.app_file))
        self.assertTrue(os.path.exists(self.tags_file))

        # These should point at a different publish now
        new_app_file = os.path.realpath(self.app_file)
        new_tags_file = os.path.realpath(self.tags_file)

        self.assertNotEqual(old_app_file, new_app_file)
        self.assertNotEqual(old_tags_file, new_tags_file)
