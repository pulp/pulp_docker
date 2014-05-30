import json
import os
import shutil
import tempfile
import unittest

import mock
from pulp.plugins.model import Unit
from pulp.server.managers import factory
from pulp.server.managers.repo.cud import RepoManager

import data
from pulp_docker.common import constants
from pulp_docker.common.models import DockerImage
from pulp_docker.plugins.importers import upload


factory.initialize()


metadata = {
    'id1': {'parent': 'id2', 'size': 1024},
    'id2': {'parent': 'id3', 'size': 1024},
    'id3': {'parent': 'id4', 'size': 1024},
    'id4': {'parent': None, 'size': 1024},
}

metadata_shared_parents_multiple_leaves = {
    'id1': {'parent': 'id2', 'size': 1024},
    'id2': {'parent': 'id3', 'size': 1024},
    'id3': {'parent': 'id5', 'size': 1024},
    'id4': {'parent': 'id5', 'size': 1024},
    'id5': {'parent': None, 'size': 1024},
}


class TestGetModels(unittest.TestCase):
    def test_full_metadata(self):
        # Test for simple metadata
        models = upload.get_models(metadata)

        self.assertEqual(len(models), len(metadata))
        for m in models:
            self.assertTrue(isinstance(m, DockerImage))
            self.assertTrue(m.image_id in metadata)

        ids = [m.image_id for m in models]
        self.assertEqual(set(ids), set(metadata.keys()))

        # Test for metadata having shared parents and multiple leaves
        models = upload.get_models(metadata_shared_parents_multiple_leaves)

        self.assertEqual(len(models), len(metadata_shared_parents_multiple_leaves))
        for m in models:
            self.assertTrue(isinstance(m, DockerImage))
            self.assertTrue(m.image_id in metadata_shared_parents_multiple_leaves)

        ids = [m.image_id for m in models]
        self.assertEqual(set(ids), set(metadata_shared_parents_multiple_leaves.keys()))

    def test_mask(self):
        # Test for simple metadata
        models = upload.get_models(metadata, mask_id='id3')

        self.assertEqual(len(models), 2)
        # make sure this only returns the first two and masks the others
        for m in models:
            self.assertTrue(m.image_id in ['id1', 'id2'])

        # Test for metadata having shared parents and multiple leaves
        models = upload.get_models(metadata_shared_parents_multiple_leaves, mask_id='id3')

        self.assertEqual(len(models), 3)
        for m in models:
            self.assertTrue(m.image_id in ['id1', 'id2', 'id4'])


class TestSaveModels(unittest.TestCase):
    def setUp(self):
        self.conduit = mock.MagicMock()

    @mock.patch('os.path.exists', return_value=True, spec_set=True)
    def test_path_exists(self, mock_exists):
        model = DockerImage('abc123', 'xyz789', 1024)

        upload.save_models(self.conduit, [model], (model.image_id,), data.busybox_tar_path)

        self.assertEqual(self.conduit.save_unit.call_count, 1)
        self.conduit.init_unit.assert_called_once_with(constants.IMAGE_TYPE_ID, model.unit_key,
                                                       model.unit_metadata, model.relative_path)

        self.conduit.save_unit.assert_called_once_with(self.conduit.init_unit.return_value)

    def test_with_busybox(self):
        models = [
            DockerImage(data.busybox_ids[0], data.busybox_ids[1], 1024),
        ]
        dest = tempfile.mkdtemp()
        try:
            # prepare some state
            model_dest = os.path.join(dest, models[0].relative_path)
            unit = Unit(DockerImage.TYPE_ID, models[0].unit_key,
                        models[0].unit_metadata, model_dest)
            self.conduit.init_unit.return_value = unit

            # call the save, letting it write files to disk
            upload.save_models(self.conduit, models, data.busybox_ids, data.busybox_tar_path)

            # assertions!
            self.conduit.save_unit.assert_called_once_with(unit)

            # make sure the ancestry was computed and saved correctly
            ancestry = json.load(open(os.path.join(model_dest, 'ancestry')))
            self.assertEqual(set(ancestry), set(data.busybox_ids))
            # make sure these files were moved into place
            self.assertTrue(os.path.exists(os.path.join(model_dest, 'json')))
            self.assertTrue(os.path.exists(os.path.join(model_dest, 'layer')))
        finally:
            shutil.rmtree(dest)


@mock.patch.object(RepoManager, 'get_repo_scratchpad', spec_set=True)
@mock.patch.object(RepoManager, 'update_repo_scratchpad', spec_set=True)
class TestUpdateTags(unittest.TestCase):
    def test_basic_update(self, mock_update, mock_get):
        mock_get.return_value = {'foo': 'other data that should not be part of the update'}

        upload.update_tags('repo1', data.busybox_tar_path)

        mock_update.assert_called_once_with('repo1', {'tags': {'latest': data.busybox_ids[0]}})

    def test_preserves_existing_tags(self, mock_update, mock_get):
        mock_get.return_value = {'tags': {'greatest': data.busybox_ids[1]}}

        upload.update_tags('repo1', data.busybox_tar_path)

        expected_tags = {
            'tags': {
                'latest': data.busybox_ids[0],
                'greatest': data.busybox_ids[1],
            }
        }
        mock_update.assert_called_once_with('repo1', expected_tags)
