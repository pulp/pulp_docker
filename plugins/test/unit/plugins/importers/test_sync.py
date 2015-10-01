import inspect
import json
import os
import shutil
import tempfile
import unittest

import mock
from nectar.request import DownloadRequest
from pulp.common.plugins import importer_constants, reporting_constants
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import Repository as RepositoryModel, Unit
from pulp.server.exceptions import MissingValue
from pulp.server.managers import factory

from pulp_docker.common import constants
from pulp_docker.plugins.importers import sync
from pulp_docker.plugins import registry


factory.initialize()


class TestSyncStep(unittest.TestCase):
    def setUp(self):
        super(TestSyncStep, self).setUp()

        self.repo = RepositoryModel('repo1')
        self.conduit = mock.MagicMock()
        plugin_config = {
            constants.CONFIG_KEY_UPSTREAM_NAME: 'pulp/crane',
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)
        self.step = sync.SyncStep(self.repo, self.conduit, self.config, '/a/b/c')

    @mock.patch.object(sync.SyncStep, 'validate')
    def test_init(self, mock_validate):
        # re-run this with the mock in place
        self.step = sync.SyncStep(self.repo, self.conduit, self.config, '/a/b/c')

        self.assertEqual(self.step.step_id, constants.SYNC_STEP_MAIN)

        # make sure the children are present
        step_ids = set([child.step_id for child in self.step.children])
        self.assertTrue(constants.SYNC_STEP_METADATA in step_ids)
        self.assertTrue(reporting_constants.SYNC_STEP_GET_LOCAL in step_ids)
        self.assertTrue(constants.SYNC_STEP_DOWNLOAD in step_ids)
        self.assertTrue(constants.SYNC_STEP_SAVE in step_ids)

        # make sure it instantiated a Repository object
        self.assertTrue(isinstance(self.step.index_repository, registry.Repository))
        self.assertEqual(self.step.index_repository.name, 'pulp/crane')
        self.assertEqual(self.step.index_repository.registry_url, 'http://pulpproject.org/')

        # these are important because child steps will populate them with data
        self.assertEqual(self.step.available_units, [])
        self.assertEqual(self.step.tags, {})

        mock_validate.assert_called_once_with(self.config)

    def test_validate_pass(self):
        self.step.validate(self.config)

    def test_validate_no_name_or_feed(self):
        config = PluginCallConfiguration({}, {})

        try:
            self.step.validate(config)
        except MissingValue, e:
            self.assertTrue(importer_constants.KEY_FEED in e.property_names)
            self.assertTrue(constants.CONFIG_KEY_UPSTREAM_NAME in e.property_names)
        else:
            raise AssertionError('validation should have failed')

    def test_validate_no_name(self):
        config = PluginCallConfiguration({}, {importer_constants.KEY_FEED: 'http://foo'})

        try:
            self.step.validate(config)
        except MissingValue, e:
            self.assertTrue(constants.CONFIG_KEY_UPSTREAM_NAME in e.property_names)
            self.assertEqual(len(e.property_names), 1)
        else:
            raise AssertionError('validation should have failed')

    def test_validate_no_feed(self):
        config = PluginCallConfiguration({}, {constants.CONFIG_KEY_UPSTREAM_NAME: 'centos'})

        try:
            self.step.validate(config)
        except MissingValue, e:
            self.assertTrue(importer_constants.KEY_FEED in e.property_names)
            self.assertEqual(len(e.property_names), 1)
        else:
            raise AssertionError('validation should have failed')

    def test_generate_download_requests(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})
        self.step.working_dir = tempfile.mkdtemp()

        try:
            generator = self.step.generate_download_requests()
            self.assertTrue(inspect.isgenerator(generator))

            download_reqs = list(generator)

            self.assertEqual(len(download_reqs), 3)
            for req in download_reqs:
                self.assertTrue(isinstance(req, DownloadRequest))
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_requests_correct_urls(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})
        self.step.working_dir = tempfile.mkdtemp()

        try:
            generator = self.step.generate_download_requests()

            # make sure the urls are correct
            urls = [req.url for req in generator]
            self.assertTrue('http://pulpproject.org/v1/images/image1/ancestry' in urls)
            self.assertTrue('http://pulpproject.org/v1/images/image1/json' in urls)
            self.assertTrue('http://pulpproject.org/v1/images/image1/layer' in urls)
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_requests_correct_destinations(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})
        self.step.working_dir = tempfile.mkdtemp()

        try:
            generator = self.step.generate_download_requests()

            # make sure the urls are correct
            destinations = [req.destination for req in generator]
            self.assertTrue(os.path.join(self.step.working_dir, 'image1', 'ancestry')
                            in destinations)
            self.assertTrue(os.path.join(self.step.working_dir, 'image1', 'json')
                            in destinations)
            self.assertTrue(os.path.join(self.step.working_dir, 'image1', 'layer')
                            in destinations)
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_reqs_creates_dir(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})
        self.step.working_dir = tempfile.mkdtemp()

        try:
            list(self.step.generate_download_requests())

            # make sure it created the destination directory
            self.assertTrue(os.path.isdir(os.path.join(self.step.working_dir, 'image1')))
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_reqs_existing_dir(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})
        self.step.working_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.step.working_dir, 'image1'))

        try:
            # just make sure this doesn't complain
            list(self.step.generate_download_requests())
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_reqs_perm_denied(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})

        # make sure the permission denies OSError bubbles up
        self.assertRaises(OSError, list, self.step.generate_download_requests())

    def test_generate_download_reqs_ancestry_exists(self):
        self.step.step_get_local_units.units_to_download.append({'image_id': 'image1'})
        self.step.working_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.step.working_dir, 'image1'))
        # simulate the ancestry file already existing
        open(os.path.join(self.step.working_dir, 'image1/ancestry'), 'w').close()

        try:
            # there should only be 2 reqs instead of 3, since the ancestry file already exists
            reqs = list(self.step.generate_download_requests())
            self.assertEqual(len(reqs), 2)
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_sync(self):
        with mock.patch.object(self.step, 'process_lifecycle') as mock_process:
            report = self.step.sync()

        # make sure we called the process_lifecycle method
        mock_process.assert_called_once_with()
        # make sure it returned a report generated by the conduit
        self.assertTrue(report is self.conduit.build_success_report.return_value)


class TestGetMetadataStep(unittest.TestCase):
    def setUp(self):
        super(TestGetMetadataStep, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.repo = RepositoryModel('repo1')
        self.repo.working_dir = self.working_dir
        self.conduit = mock.MagicMock()
        plugin_config = {
            constants.CONFIG_KEY_UPSTREAM_NAME: 'pulp/crane',
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)

        self.step = sync.GetMetadataStep(self.repo, self.conduit, self.config, self.working_dir)
        self.step.parent = mock.MagicMock()
        self.index = self.step.parent.index_repository

    def tearDown(self):
        super(TestGetMetadataStep, self).tearDown()
        shutil.rmtree(self.working_dir)

    def test_updates_tags(self):
        self.index.get_tags.return_value = {
            'latest': 'abc1'
        }
        self.index.get_image_ids.return_value = ['abc123']
        self.step.parent.tags = {}
        # make the ancestry file and put it in the expected place
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        with open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w') as ancestry:
            ancestry.write('["abc123"]')

        self.step.process_main()

        self.assertEqual(self.step.parent.tags, {'latest': 'abc123'})

    def test_updates_available_units(self):
        self.index.get_tags.return_value = {
            'latest': 'abc1'
        }
        self.index.get_image_ids.return_value = ['abc123']
        self.step.parent.tags = {}
        # make the ancestry file and put it in the expected place
        os.makedirs(os.path.join(self.working_dir, 'abc123'))
        with open(os.path.join(self.working_dir, 'abc123/ancestry'), 'w') as ancestry:
            ancestry.write('["abc123","xyz789"]')

        self.step.process_main()

        available_ids = [unit_key['image_id'] for unit_key in self.step.parent.available_units]
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


class TestGetLocalImagesStep(unittest.TestCase):

    def setUp(self):
        super(TestGetLocalImagesStep, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.step = sync.GetLocalImagesStep(constants.IMPORTER_TYPE_ID,
                                            constants.IMAGE_TYPE_ID,
                                            ['image_id'], self.working_dir)
        self.step.conduit = mock.MagicMock()

    def tearDown(self):
        super(TestGetLocalImagesStep, self).tearDown()
        shutil.rmtree(self.working_dir)

    def test_dict_to_unit(self):
        unit = self.step._dict_to_unit({'image_id': 'abc123', 'parent_id': None, 'size': 12})

        self.assertTrue(unit is self.step.conduit.init_unit.return_value)
        self.step.conduit.init_unit.assert_called_once_with(constants.IMAGE_TYPE_ID,
                                                            {'image_id': 'abc123'}, {},
                                                            os.path.join(constants.IMAGE_TYPE_ID,
                                                                         'abc123'))


class TestSaveUnits(unittest.TestCase):
    def setUp(self):
        super(TestSaveUnits, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.dest_dir = tempfile.mkdtemp()
        self.step = sync.SaveUnits(self.working_dir)
        self.step.repo = RepositoryModel('repo1')
        self.step.conduit = mock.MagicMock()
        self.step.parent = mock.MagicMock()
        self.step.parent.step_get_local_units.units_to_download = [{'image_id': 'abc123'}]

        self.unit = Unit(constants.IMAGE_TYPE_ID, {'image_id': 'abc123'},
                         {'parent': None, 'size': 2}, os.path.join(self.dest_dir, 'abc123'))

    def tearDown(self):
        super(TestSaveUnits, self).tearDown()
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

    @mock.patch('pulp_docker.plugins.importers.tags.update_tags', spec_set=True)
    def test_process_main_copy_files(self, mock_update_tags):
        self._write_files_legit_metadata()

        with mock.patch.object(self.step, 'copy_files') as mock_copy_files:
            self.step.process_main()

        expected_unit = self.step.conduit.init_unit.return_value
        mock_copy_files.assert_called_once_with(expected_unit)

    @mock.patch('pulp_docker.plugins.importers.tags.update_tags', spec_set=True)
    def test_process_main_saves_unit(self, mock_update_tags):
        self._write_files_legit_metadata()

        with mock.patch.object(self.step, 'copy_files'):
            self.step.process_main()

        expected_unit = self.step.conduit.init_unit.return_value
        self.step.conduit.save_unit.assert_called_once_with(expected_unit)

    @mock.patch('pulp_docker.plugins.importers.tags.update_tags', spec_set=True)
    def test_process_main_updates_tags(self, mock_update_tags):
        self._write_files_legit_metadata()
        self.step.parent.tags = {'latest': 'abc123'}

        with mock.patch.object(self.step, 'copy_files'):
            self.step.process_main()

        mock_update_tags.assert_called_once_with(self.step.repo.id, {'latest': 'abc123'})

    def test_copy_files_make_dir(self):
        self._write_empty_files()

        self.step.copy_files(self.unit)

        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, 'abc123/ancestry')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, 'abc123/json')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, 'abc123/layer')))

        self.assertTrue(os.path.exists(os.path.join(self.working_dir, 'abc123/ancestry')))
        self.assertTrue(os.path.exists(os.path.join(self.working_dir, 'abc123/json')))
        self.assertTrue(os.path.exists(os.path.join(self.working_dir, 'abc123/layer')))

    def test_copy_files_dir_exists(self):
        self._write_empty_files()
        os.makedirs(os.path.join(self.dest_dir, 'abc123'))

        self.step.copy_files(self.unit)

        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, 'abc123/ancestry')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, 'abc123/json')))
        self.assertTrue(os.path.exists(os.path.join(self.dest_dir, 'abc123/layer')))

        self.assertTrue(os.path.exists(os.path.join(self.working_dir, 'abc123/ancestry')))
        self.assertTrue(os.path.exists(os.path.join(self.working_dir, 'abc123/json')))
        self.assertTrue(os.path.exists(os.path.join(self.working_dir, 'abc123/layer')))

    def test_copy_files_makedirs_fails(self):
        self.unit.storage_path = '/a/b/c'

        # make sure that a permission denied error bubbles up
        self.assertRaises(OSError, self.step.copy_files, self.unit)
