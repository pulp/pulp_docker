import json
import os
import shutil
import tempfile
import unittest

import mock
from pulp.common.plugins import importer_constants
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository as RepositoryModel, Unit
from pulp.server.managers import factory

from pulp_docker.common import constants
from pulp_docker.plugins.importers import v1_sync


factory.initialize()


class TestGetMetadataStep(unittest.TestCase):
    def setUp(self):
        super(TestGetMetadataStep, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.repo = RepositoryModel('repo1')
        self.conduit = mock.MagicMock()
        plugin_config = {
            constants.CONFIG_KEY_UPSTREAM_NAME: 'pulp/crane',
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)

        self.step = v1_sync.GetMetadataStep(repo=self.repo, conduit=self.conduit,
                                            config=self.config)
        self.step.working_dir = self.working_dir
        self.step.parent = mock.MagicMock()
        self.index = self.step.parent.v1_index_repository

    def tearDown(self):
        super(TestGetMetadataStep, self).tearDown()
        shutil.rmtree(self.working_dir)

    def test_updates_tags(self):
        self.index.get_tags.return_value = {
            'latest': 'abc1'
        }
        self.index.get_image_ids.return_value = ['abc123']
        self.step.parent.v1_tags = {}
        # make the ancestry file and put it in the expected place
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        with open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w') as ancestry:
            ancestry.write('["abc123"]')

        self.step.process_main()

        self.assertEqual(self.step.parent.v1_tags, {'latest': 'abc123'})

    def test_updates_available_units(self):
        self.index.get_tags.return_value = {
            'latest': 'abc1'
        }
        self.index.get_image_ids.return_value = ['abc123']
        self.step.parent.v1_tags = {}
        self.step.parent.v1_available_units = []
        # make the ancestry file and put it in the expected place
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        with open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w') as ancestry:
            ancestry.write('["abc123","xyz789"]')

        self.step.process_main()

        available_ids = [image.image_id for image in self.step.parent.v1_available_units]
        self.assertTrue('abc123' in available_ids)
        self.assertTrue('xyz789' in available_ids)

    def test_expand_tags_no_abbreviations(self):
        ids = ['abc123', 'xyz789']
        tags = {'foo': 'abc123', 'bar': 'abc123', 'baz': 'xyz789'}

        self.step.expand_tag_abbreviations(ids, tags)
        self.assertEqual(tags['foo'], 'abc123')
        self.assertEqual(tags['bar'], 'abc123')
        self.assertEqual(tags['baz'], 'xyz789')

    def test_expand_tags_with_abbreviations(self):
        ids = ['abc123', 'xyz789']
        tags = {'foo': 'abc', 'bar': 'abc123', 'baz': 'xyz'}

        self.step.expand_tag_abbreviations(ids, tags)
        self.assertEqual(tags['foo'], 'abc123')
        self.assertEqual(tags['bar'], 'abc123')
        self.assertEqual(tags['baz'], 'xyz789')

    def test_find_and_read_ancestry_file(self):
        # make the ancestry file and put it in the expected place
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        with open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w') as ancestry:
            ancestry.write('["abc123","xyz789"]')

        ancester_ids = self.step.find_and_read_ancestry_file('abc123', self.working_dir)

        self.assertEqual(ancester_ids, ['abc123', 'xyz789'])


class TestSaveImages(unittest.TestCase):
    def setUp(self):
        super(TestSaveImages, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.dest_dir = tempfile.mkdtemp()
        self.step = v1_sync.SaveImages(self.working_dir)
        self.step.repo = RepositoryModel('repo1')
        self.step.conduit = mock.MagicMock()
        self.step.parent = mock.MagicMock()
        self.step.parent.step_get_local_units.units_to_download = [{'image_id': 'abc123'}]

        self.unit = Unit(constants.IMAGE_TYPE_ID, {'image_id': 'abc123'},
                         {'parent': None, 'size': 2}, os.path.join(self.dest_dir, 'abc123'))

    def tearDown(self):
        super(TestSaveImages, self).tearDown()
        shutil.rmtree(self.working_dir)
        shutil.rmtree(self.dest_dir)

    def _write_empty_files(self):
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w').close()
        open(os.path.join(self.working_dir, 'abc123/json'), 'w').close()
        open(os.path.join(self.working_dir, 'abc123/layer'), 'w').close()

    def _write_files_legit_metadata(self):
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w').close()
        open(os.path.join(self.working_dir, 'abc123/layer'), 'w').close()
        # write just enough metadata to make the step happy
        with open(os.path.join(self.working_dir, 'abc123/json'), 'w') as json_file:
            json.dump({'Size': 2, 'Parent': 'xyz789'}, json_file)
