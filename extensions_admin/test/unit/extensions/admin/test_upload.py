import unittest

import mock

from pulp_docker.common import constants
from pulp_docker.extensions.admin.upload import UploadDockerImageCommand, \
    OPT_MASK_ANCESTOR_ID, TagUpdateCommand, TAG_NAME_OPTION, \
    DIGEST_OPTION
from pulp.client.commands import options as std_options
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

    def test_determine_id_wth_image(self):
        ret = self.command.determine_type_id(data.busybox_tar_path)
        self.assertEqual(ret, constants.IMAGE_TYPE_ID)

    def test_determine_id_with_blob(self):
        ret = self.command.determine_type_id(data.skopeo_tar_path)
        self.assertEqual(ret, constants.MANIFEST_TYPE_ID)

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


class TestTagUpdateCommand(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.config = test_config
        self.command = TagUpdateCommand(self.context)

    def test_determine_id(self):
        ret = self.command.determine_type_id('/a/b/c')
        self.assertEqual(ret, constants.TAG_TYPE_ID)

    def test_generate_unit_key(self):
        kwargs = {TAG_NAME_OPTION.keyword: data.tag_name,
                  std_options.OPTION_REPO_ID.keyword: data.repo_id}
        unit_key = self.command.generate_unit_key(data.busybox_tar_path, **kwargs)
        self.assertEqual(unit_key, {'name': data.tag_name, 'repo_id': data.repo_id})

    def test_generate_metadata(self):
        kwargs = {TAG_NAME_OPTION.keyword: data.tag_name,
                  DIGEST_OPTION.keyword: data.manifest_digest}
        metadata = self.command.generate_metadata(data.busybox_tar_path, **kwargs)
        self.assertEqual(metadata, {'name': data.tag_name, 'digest': data.manifest_digest})

    def test_generate_override_config(self):
        ret = self.command.generate_override_config()
        self.assertEqual(ret, {})
