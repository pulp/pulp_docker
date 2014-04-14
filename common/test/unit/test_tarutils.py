import os
import unittest

import mock

from pulp_docker.common import tarutils


busybox_tar_path = os.path.join(os.path.dirname(__file__), '../data/busyboxlight.tar')

# these are in correct ancestry order
busybox_ids = (
    '769b9341d937a3dba9e460f664b4f183a6cecdd62b337220a28b3deb50ee0a02',
    '48e5f45168b97799ad0aafb7e2fef9fac57b5f16f6db7f67ba2000eb947637eb',
    'bf747efa0e2fa9f7c691588ce3938944c75607a7bb5e757f7369f86904d97c78',
    '511136ea3c5a64f264b78b5433614aec563103b4d4702f3ba7d4d2698e22c158',
)


class TestGetMetadata(unittest.TestCase):
    def test_path_does_not_exist(self):
        self.assertRaises(IOError, tarutils.get_metadata, '/a/b/c/d')

    def test_get_from_busybox(self):
        metadata = tarutils.get_metadata(busybox_tar_path)

        self.assertEqual(set(metadata.keys()), set(busybox_ids))
        for i, image_id in enumerate(busybox_ids):
            data = metadata[image_id]
            if i == len(busybox_ids) - 1:
                # make sure the base image has parent set to None
                self.assertTrue(data['parent'] is None)
            else:
                # make sure all other layers have the correct parent
                self.assertEqual(data['parent'], busybox_ids[i + 1])

            self.assertTrue(isinstance(data['size'], int))


class TestGetTags(unittest.TestCase):
    def test_normal(self):
        tags = tarutils.get_tags(busybox_tar_path)

        self.assertEqual(tags, {'latest': busybox_ids[0]})

    @mock.patch('json.load', spec_set=True)
    def test_no_repos(self, mock_load):
        mock_load.return_value = {}

        self.assertRaises(ValueError, tarutils.get_tags, busybox_tar_path)


class TestGetAncestry(unittest.TestCase):
    def test_from_busybox(self):
        metadata = tarutils.get_metadata(busybox_tar_path)
        ancestry = tarutils.get_ancestry(busybox_ids[0], metadata)

        self.assertEqual(ancestry, busybox_ids)


class TestGetYoungestChild(unittest.TestCase):
    def test_path_does_not_exist(self):
        self.assertRaises(IOError, tarutils.get_youngest_child, '/a/b/c/d')

    def test_with_busybox(self):
        ret = tarutils.get_youngest_child(busybox_tar_path)

        self.assertEqual(ret, busybox_ids[0])
