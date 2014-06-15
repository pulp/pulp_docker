import unittest

import mock

from pulp_docker.common import constants
from pulp_docker.extensions.admin.upload import UploadDockerImageCommand, OPT_MASK_ANCESTOR_ID
import data


test_config = {
    'filesystem': {'upload_working_dir': '~/.pulp/upload/'},
    'output': {'poll_frequency_in_seconds': 2},
}


class TestUploadDockerImageCommand(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.config = test_config
        self.command = UploadDockerImageCommand(self.context)

    def test_determine_id(self):
        ret = self.command.determine_type_id('/a/b/c')
        self.assertEqual(ret, constants.IMAGE_TYPE_ID)

    def test_generate_unit_key_and_metadata(self):
        unit_key, metadata = self.command.generate_unit_key_and_metadata(data.busybox_tar_path)
        self.assertEqual(unit_key, {})
        self.assertEqual(metadata, {})

    def test_generate_override_config(self):
        ret = self.command.generate_override_config()
        self.assertEqual(ret, {})

    def test_generate_override_config_with_mask_id(self):
        test_mask_id = 'test-mask-id'
        kwargs = {OPT_MASK_ANCESTOR_ID.keyword: test_mask_id}
        ret = self.command.generate_override_config(**kwargs)
        self.assertEqual(ret, {constants.CONFIG_KEY_MASK_ID: test_mask_id})

    def test_generate_override_config_with_random_option(self):
        kwargs = {'random': 'test_random_option'}
        ret = self.command.generate_override_config(**kwargs)
        self.assertEqual(ret, {})
