import stat
try:
    import unittest2 as unittest
except ImportError:
    import unittest


import mock
from pulp.common.plugins import reporting_constants

from pulp_docker.common import constants
from pulp_docker.plugins.importers import upload


class TestAddDockerUnits(unittest.TestCase):

    @mock.patch('pulp_docker.plugins.importers.upload.os.chmod')
    @mock.patch('pulp_docker.plugins.importers.upload.os.walk')
    @mock.patch('pulp_docker.plugins.importers.upload.tarfile.open')
    def test_initialize(self, mock_tarfile_open, mock_walk, mock_chmod):
        """
        Test that the initialize properly extracts the archive and then fixes the permissions
        """
        parent_step = upload.PluginStep('parent', working_dir='bar')
        step = upload.AddDockerUnits(tarfile_path='foo')
        parent_step.add_child(step)

        walk_dirs = ['apple']
        walk_files = ['pear']
        mock_walk.return_value = [('fruit', walk_dirs, walk_files)]

        step.initialize()

        # Confirm that the tar was extracted
        mock_tarfile_open.assert_called_once_with('foo')
        mock_tarfile_open.return_value.extractall.assert_called_once_wth('bar')

        # Confirm that the file permissions were fixed on the extracted files
        expected_calls = [mock.call('fruit/apple', stat.S_IXUSR | stat.S_IWUSR | stat.S_IREAD),
                          mock.call('fruit/pear', stat.S_IXUSR | stat.S_IWUSR | stat.S_IREAD)]
        self.assertEquals(mock_chmod.call_args_list, expected_calls)

    @mock.patch('pulp_docker.plugins.importers.upload.AddDockerUnits._associate_item')
    @mock.patch('pulp_docker.plugins.importers.upload.json')
    @mock.patch('pulp_docker.plugins.importers.upload.tarutils.get_ancestry')
    def test_process_main(self, mock_get_ancestry, mock_json, mock_associate_item):
        """
        Test the association of a single layer

        Mock out the _associate_item in the parent class
        """
        step = upload.AddDockerUnits(tarfile_path='foo')
        step.parent = mock.MagicMock()
        step.working_dir = 'bar'

        m_open = mock.mock_open()
        with mock.patch('__builtin__.open', m_open, create=True):
            step.process_main(mock.Mock(image_id='baz'))

        m_open.assert_called_once_with('bar/baz/ancestry', 'w')

        mock_get_ancestry.assert_called_once_with('baz', step.parent.metadata)
        mock_json.dump.assert_called_once_with(mock_get_ancestry.return_value, m_open.return_value)


class TestProcessMetadata(unittest.TestCase):

    @mock.patch('pulp_docker.plugins.importers.upload.tarutils.get_tags')
    @mock.patch('pulp_docker.plugins.importers.upload.tarutils.get_metadata')
    @mock.patch('pulp_docker.plugins.importers.upload.ProcessMetadata.get_models')
    @mock.patch('pulp_docker.plugins.importers.upload.ProcessMetadata.get_config')
    def test_process_main(self, mock_get_config, mock_get_models, mock_get_metadata, mock_tags):
        step = upload.ProcessMetadata(file_path='foo')
        mock_get_config.return_value = {constants.CONFIG_KEY_MASK_ID: 'a'}
        step.parent = mock.MagicMock(metadata=None, available_units=None, tags=None,
                                     get_config=mock.Mock(return_value='a'))
        step.process_main()
        mock_get_metadata.assert_called_once_with('foo')
        mock_get_models.assert_called_once_with(mock_get_metadata.return_value, 'a')
        mock_tags.assert_called_once_with('foo')

        self.assertEquals(step.parent.metadata, mock_get_metadata.return_value)
        self.assertEquals(step.parent.available_units, mock_get_models.return_value)
        self.assertEquals(step.parent.tags, mock_tags.return_value)

    @mock.patch('pulp_docker.plugins.importers.upload.tarutils.get_youngest_children')
    def test_get_models(self, mock_get_children):
        step = upload.ProcessMetadata(file_path='foo')

        metadata = {
            'id1': {'parent': 'id2', 'size': 1024},
            'id2': {'parent': 'id3', 'size': 1024},
            'id3': {'parent': 'id4', 'size': 1024},
            'id4': {'parent': None, 'size': 1024},
        }
        mock_get_children.return_value = ['id1']
        images = step.get_models(metadata)

        self.assertTrue(len(images), 4)
        self.assertEquals(images[0].image_id, 'id1')
        self.assertEquals(images[0].parent_id, 'id2')
        self.assertEquals(images[0].size, 1024)
        self.assertEquals(images[3].image_id, 'id4')
        self.assertEquals(images[3].parent_id, None)
        self.assertEquals(images[3].size, 1024)

    @mock.patch('pulp_docker.plugins.importers.upload.tarutils.get_youngest_children')
    def test_get_models_masking(self, mock_get_children):
        """
        Test that masking works properly
        """
        step = upload.ProcessMetadata(file_path='foo')

        metadata = {
            'id1': {'parent': 'id2', 'size': 1024},
            'id2': {'parent': 'id3', 'size': 1024},
            'id3': {'parent': 'id4', 'size': 1024},
            'id4': {'parent': None, 'size': 1024},
        }
        mock_get_children.return_value = ['id1']
        images = step.get_models(metadata, mask_id='id3')

        self.assertTrue(len(images), 2)
        self.assertEquals(images[0].image_id, 'id1')
        self.assertEquals(images[0].parent_id, 'id2')
        self.assertEquals(images[0].size, 1024)
        self.assertEquals(images[1].image_id, 'id2')
        self.assertEquals(images[1].parent_id, 'id3')
        self.assertEquals(images[1].size, 1024)


class TestUploadStep(unittest.TestCase):

    # @mock.patch('pulp_docker.plugins.importers.upload.')
    def test_init(self):
        """
        Validate that the construction works ok
        """
        step = upload.UploadStep(file_path='foo_file_path')
        self.assertEqual(step.step_id, constants.UPLOAD_STEP)

        # make sure the children are present
        step_ids = set([child.step_id for child in step.children])
        expected_steps = set((
            constants.UPLOAD_STEP_METADATA,
            reporting_constants.SYNC_STEP_GET_LOCAL,
            constants.UPLOAD_STEP_SAVE
        ))

        self.assertSetEqual(step_ids, expected_steps)

        # these are important because child steps will populate them with data
        self.assertEqual(step.available_units, [])
        self.assertEqual(step.tags, {})
