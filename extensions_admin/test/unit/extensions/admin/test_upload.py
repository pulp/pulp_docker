import unittest

import mock

from pulp_docker.common import constants
from pulp_docker.extensions.admin.upload import UploadDockerImageCommand
import data


class TestDetermineID(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.config = {'filesystem': {'upload_working_dir': '~/.pulp/upload/'}}
        self.command = UploadDockerImageCommand(self.context)

    def test_return_value(self):
        ret = self.command.determine_type_id('/a/b/c')

        self.assertEqual(ret, constants.IMAGE_TYPE_ID)


class TestGenerateUnitKeyAndMetadata(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.config = {'filesystem': {'upload_working_dir': '~/.pulp/upload/'}}
        self.command = UploadDockerImageCommand(self.context)

    def test_with_busybox(self):
        unit_key, metadata = self.command.generate_unit_key_and_metadata(data.busybox_tar_path)

        self.assertEqual(unit_key, {'image_id': data.busybox_ids[0]})
        self.assertEqual(metadata, {})

    def test_file_does_not_exist(self):
        self.assertRaises(IOError, self.command.generate_unit_key_and_metadata, '/a/b/c/d')
