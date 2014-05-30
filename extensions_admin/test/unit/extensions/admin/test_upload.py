import unittest

import mock

from pulp_docker.common import constants
from pulp_docker.extensions.admin.upload import UploadDockerImageCommand
import data


test_config = {
    'filesystem': {'upload_working_dir': '~/.pulp/upload/'},
    'output': {'poll_frequency_in_seconds': 2},
}


class TestDetermineID(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.config = test_config
        self.command = UploadDockerImageCommand(self.context)

    def test_return_value(self):
        ret = self.command.determine_type_id('/a/b/c')

        self.assertEqual(ret, constants.IMAGE_TYPE_ID)


class TestGenerateUnitKeyAndMetadata(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.config = test_config
        self.command = UploadDockerImageCommand(self.context)

    def test_with_busybox(self):
        unit_key, metadata = self.command.generate_unit_key_and_metadata(data.busybox_tar_path)

        self.assertEqual(unit_key, {})
        self.assertEqual(metadata, {})
