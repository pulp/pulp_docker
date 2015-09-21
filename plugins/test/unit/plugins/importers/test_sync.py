import inspect
import os
import shutil
import tempfile
try:
    import unittest2 as unittest
except ImportError:
    import unittest


import mock
from nectar.request import DownloadRequest
from pulp.common.plugins import importer_constants, reporting_constants
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db import models as platform_model
from pulp.server.exceptions import MissingValue

from pulp_docker.common import constants
from pulp_docker.plugins.db import models
from pulp_docker.plugins.importers import sync
from pulp_docker.plugins import registry


class TestSyncStep(unittest.TestCase):
    def setUp(self):
        super(TestSyncStep, self).setUp()

        self.repo = platform_model.Repository(repo_id='repo1')
        self.conduit = mock.MagicMock()
        plugin_config = {
            constants.CONFIG_KEY_UPSTREAM_NAME: 'pulp/crane',
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)
        self.step = sync.SyncStep(self.repo, self.conduit, self.config, working_dir='/a/b/c')

    @mock.patch.object(sync.SyncStep, 'validate')
    def test_init(self, mock_validate):
        # re-run this with the mock in place
        self.step = sync.SyncStep(self.repo, self.conduit, self.config, working_dir='/a/b/c')

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
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))
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
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))
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
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))
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
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))
        self.step.working_dir = tempfile.mkdtemp()

        try:
            list(self.step.generate_download_requests())

            # make sure it created the destination directory
            self.assertTrue(os.path.isdir(os.path.join(self.step.working_dir, 'image1')))
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_reqs_existing_dir(self):
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))
        self.step.working_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.step.working_dir, 'image1'))

        try:
            # just make sure this doesn't complain
            list(self.step.generate_download_requests())
        finally:
            shutil.rmtree(self.step.working_dir)

    def test_generate_download_reqs_perm_denied(self):
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))

        # make sure the permission denies OSError bubbles up
        self.assertRaises(OSError, list, self.step.generate_download_requests())

    def test_generate_download_reqs_ancestry_exists(self):
        self.step.step_get_local_units.units_to_download.append(
            models.DockerImage(image_id='image1'))
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


class TestGetMetadataStep(unittest.TestCase):
    def setUp(self):
        super(TestGetMetadataStep, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.repo = platform_model.Repository(repo_id='repo1')
        self.repo.working_dir = self.working_dir
        self.conduit = mock.MagicMock()
        plugin_config = {
            constants.CONFIG_KEY_UPSTREAM_NAME: 'pulp/crane',
            importer_constants.KEY_FEED: 'http://pulpproject.org/',
        }
        self.config = PluginCallConfiguration({}, plugin_config)

        self.step = sync.GetMetadataStep(self.repo, self.conduit, self.config,
                                         working_dir=self.working_dir)
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


class TestSaveDockerUnits(unittest.TestCase):
    def setUp(self):
        self.step = sync.SaveDockerUnits()
        self.step.conduit = mock.MagicMock()
        self.step.parent = mock.MagicMock()
        self.unit = models.DockerImage(image_id='abc123', size=2)
        self.step.parent.step_get_local_units.units_to_download = [self.unit]

    def test_get_iterator(self):
        unit = models.DockerImage(image_id='abc123', size=2)
        step = sync.SaveDockerUnits()
        step.parent = mock.MagicMock(step_get_local_units=mock.Mock(units_to_download=[unit]))

        result = list(step.get_iterator())

        self.assertListEqual(result, step.parent.step_get_local_units.units_to_download)

    @mock.patch('pulp_docker.plugins.importers.sync.SaveDockerUnits._associate_item')
    def test_process_main(self, mock_associate):
        unit = models.DockerImage(image_id='abc123', size=2)
        step = sync.SaveDockerUnits()

        step.process_main(item=unit)

        mock_associate.assert_called_once_with(unit)

    @mock.patch('pulp_docker.plugins.importers.sync.models.DockerImage.set_content')
    @mock.patch('pulp_docker.plugins.importers.sync.SaveDockerUnits.get_working_dir',
                return_value='wdir')
    @mock.patch('pulp_docker.plugins.importers.sync.json.load')
    @mock.patch('pulp_docker.plugins.importers.sync.models.DockerImage.save')
    @mock.patch('pulp_docker.plugins.importers.sync.repo_controller.associate_single_unit')
    def test__associate_item(self, mock_associate, mock_save, mock_load, m_get_working_dir,
                             m_set_content):
        """
        Test the associate item with a parent specified with a P in the metadata "Parent"
        """
        unit = models.DockerImage(image_id='abc123')
        step = sync.SaveDockerUnits()
        step.repo = 'foo_repo'
        mock_load.return_value = {'Size': 2, 'Parent': 'foo'}

        m_open = mock.mock_open()
        with mock.patch('__builtin__.open', m_open, create=True):
            step._associate_item(unit)

        m_open.assert_called_once_with('wdir/abc123/json')
        m_set_content.assert_called_once_with('wdir/abc123')

        self.assertEquals(unit.size, 2)
        self.assertEquals(unit.parent_id, 'foo')

        mock_save.assert_called_once_with()
        mock_associate.assert_called_once_with('foo_repo', unit)

    @mock.patch('pulp_docker.plugins.importers.sync.models.DockerImage.set_content')
    @mock.patch('pulp_docker.plugins.importers.sync.SaveDockerUnits.get_working_dir',
                return_value='wdir')
    @mock.patch('pulp_docker.plugins.importers.sync.json.load')
    @mock.patch('pulp_docker.plugins.importers.sync.models.DockerImage.save')
    @mock.patch('pulp_docker.plugins.importers.sync.repo_controller.associate_single_unit')
    def test__associate_item_parent(self, mock_associate, mock_save, mock_load, m_get_working_dir,
                                    m_set_content):
        """
        Test the associate item with a parent specified with a p in the metadata "parent"
        as the json may include either
        """
        unit = models.DockerImage(image_id='abc123')
        step = sync.SaveDockerUnits()
        step.repo = 'foo_repo'
        mock_load.return_value = {'Size': 2, 'parent': 'foo'}

        m_open = mock.mock_open()
        with mock.patch('__builtin__.open', m_open, create=True):
            step._associate_item(unit)

        m_open.assert_called_once_with('wdir/abc123/json')
        m_set_content.assert_called_once_with('wdir/abc123')

        self.assertEquals(unit.size, 2)
        self.assertEquals(unit.parent_id, 'foo')

        mock_save.assert_called_once_with()
        mock_associate.assert_called_once_with('foo_repo', unit)

    @mock.patch('pulp_docker.plugins.importers.sync.platform_models.Repository.objects')
    @mock.patch('pulp.plugins.util.publish_step.repo_controller.rebuild_content_unit_counts')
    def test_finalize_with_tags(self, m_update_count, m_repo_objects):
        """
        Test the finalize when tags have been updated
        """
        step = sync.SaveDockerUnits()
        step.repo = platform_model.Repository(repo_id='repo_bar')
        step.parent = mock.Mock(tags={'aa': 'bb'})

        step.finalize()

        m_repo_objects.assert_called_once_with(repo_id='repo_bar')

        u_one = m_repo_objects.return_value.update_one
        expected_tags = [
            {
                "image_id": "bb",
                "tag": "aa"
            }, ]
        u_one.assert_called_once_with(set__scratchpad__tags=expected_tags)
        # m_update_tags.assert_called_once_with('repo_bar', 'tag_foo')
