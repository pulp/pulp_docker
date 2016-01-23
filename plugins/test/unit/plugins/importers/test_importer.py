import unittest

import mock
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.importer import Importer
from pulp.plugins.model import Repository

import data
from pulp_docker.common import constants, models
from pulp_docker.plugins.importers.importer import DockerImporter, entry_point
from pulp_docker.plugins.importers import upload


MODULE = 'pulp_docker.plugins.importers.importer'


class TestEntryPoint(unittest.TestCase):
    def test_returns_importer(self):
        importer, config = entry_point()

        self.assertTrue(issubclass(importer, Importer))

    def test_returns_config(self):
        importer, config = entry_point()

        # make sure it's at least the correct type
        self.assertTrue(isinstance(config, dict))


class TestBasics(unittest.TestCase):
    def test_metadata(self):
        metadata = DockerImporter.metadata()

        self.assertEqual(metadata['id'], constants.IMPORTER_TYPE_ID)
        self.assertEqual(
            metadata['types'],
            [
                models.Image.TYPE_ID,
                models.Manifest.TYPE_ID,
                models.Blob.TYPE_ID
            ])
        self.assertTrue(len(metadata['display_name']) > 0)


@mock.patch('pulp_docker.plugins.importers.sync.SyncStep')
@mock.patch('tempfile.mkdtemp', spec_set=True)
@mock.patch('shutil.rmtree')
class TestSyncRepo(unittest.TestCase):
    def setUp(self):
        super(TestSyncRepo, self).setUp()
        self.repo = Repository('repo1', working_dir='/a/b/c')
        self.sync_conduit = mock.MagicMock()
        self.config = mock.MagicMock()
        self.importer = DockerImporter()

    def test_calls_sync_step(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.assert_called_once_with(repo=self.repo, conduit=self.sync_conduit,
                                               config=self.config,
                                               working_dir=mock_mkdtemp.return_value)

    def test_calls_sync(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.return_value.sync.assert_called_once_with()

    def test_makes_temp_dir(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_mkdtemp.assert_called_once_with(dir=self.repo.working_dir)

    def test_removes_temp_dir(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_rmtree.assert_called_once_with(mock_mkdtemp.return_value, ignore_errors=True)

    def test_removes_temp_dir_after_exception(self, mock_rmtree, mock_mkdtemp, mock_sync_step):
        class MyError(Exception):
            pass
        mock_sync_step.return_value.sync.side_effect = MyError
        self.assertRaises(MyError, self.importer.sync_repo, self.repo,
                          self.sync_conduit, self.config)

        mock_rmtree.assert_called_once_with(mock_mkdtemp.return_value, ignore_errors=True)


class TestCancel(unittest.TestCase):
    def setUp(self):
        super(TestCancel, self).setUp()
        self.importer = DockerImporter()

    def test_calls_cancel(self):
        self.importer.sync_step = mock.MagicMock()

        self.importer.cancel_sync_repo()

        # make sure the step's cancel method was called
        self.importer.sync_step.cancel.assert_called_once_with()


@mock.patch.object(upload, 'update_tags', spec_set=True)
class TestUploadUnit(unittest.TestCase):
    def setUp(self):
        self.unit_key = {'image_id': data.busybox_ids[0]}
        self.repo = Repository('repo1')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_save_conduit(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        conduit = mock_save.call_args[0][0]

        self.assertTrue(conduit is self.conduit)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_models(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        images = mock_save.call_args[0][1]

        for image in images:
            self.assertTrue(isinstance(image, models.Image))

        ids = [i.image_id for i in images]

        self.assertEqual(tuple(ids), data.busybox_ids)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_ancestry(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        ancestry = mock_save.call_args[0][2]

        self.assertEqual(tuple(ancestry), data.busybox_ids)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_saved_filepath(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        path = mock_save.call_args[0][3]

        self.assertEqual(path, data.busybox_tar_path)

    @mock.patch('pulp_docker.plugins.importers.upload.save_models', spec_set=True)
    def test_added_tags(self, mock_save, mock_update_tags):
        DockerImporter().upload_unit(self.repo, constants.IMAGE_TYPE_ID, self.unit_key,
                                     {}, data.busybox_tar_path, self.conduit, self.config)

        mock_update_tags.assert_called_once_with(self.repo.id, data.busybox_tar_path)


class TestImportUnits(unittest.TestCase):

    def setUp(self):
        self.unit_key = {'image_id': data.busybox_ids[0]}
        self.source_repo = Repository('repo_source')
        self.dest_repo = Repository('repo_dest')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})

    @mock.patch('pulp_docker.plugins.importers.importer.DockerImporter._import_images')
    @mock.patch('pulp_docker.plugins.importers.importer.DockerImporter._import_manifests')
    def test_import(self, import_manifests, import_images):
        import_images.return_value = [1, 2]
        import_manifests.return_value = [3, 4]
        units = mock.Mock()
        importer = DockerImporter()
        imported = importer.import_units(
            source_repo=self.source_repo,
            dest_repo=self.dest_repo,
            import_conduit=self.conduit,
            config=self.config,
            units=units)
        import_images.assert_called_once_with(self.conduit, units)
        import_manifests.assert_called_once_with(self.conduit, units)
        self.assertEqual(imported, import_images.return_value + import_manifests.return_value)

    def test_import_all_images(self):
        units = [
            mock.Mock(type_id=models.Image.TYPE_ID,
                      unit_key={'image_id': 'foo'},
                      metadata={}),
            mock.Mock(type_id='not-an-image',
                      unit_key={'image_id': 'foo'},
                      metadata={}),
        ]
        self.conduit.get_source_units.return_value = units
        result = DockerImporter()._import_images(self.conduit, None)
        self.assertEquals(result, units[0:1])
        self.conduit.associate_unit.assert_called_once_with(units[0])

    def test_import_images_no_parent(self):
        units = [
            mock.Mock(type_id=models.Image.TYPE_ID,
                      unit_key={'image_id': 'foo'},
                      metadata={}),
        ]
        result = DockerImporter()._import_images(self.conduit, units)
        self.assertEquals(result, units[0:1])
        self.conduit.associate_unit.assert_called_once_with(units[0])
        self.assertFalse(self.conduit.get_source_units.called)

    def test_import_images_with_parent(self):
        parents = [
            mock.Mock(
                id='parent',
                type_id=models.Image.TYPE_ID,
                unit_key={'image_id': 'bar-parent'},
                metadata={}),
        ]
        units = [
            mock.Mock(
                type_id=models.Image.TYPE_ID,
                unit_key={'image_id': 'foo'},
                metadata={}),
            mock.Mock(
                type_id=models.Image.TYPE_ID,
                unit_key={'image_id': 'bar'},
                metadata={'parent_id': 'bar-parent'}),
        ]
        self.conduit.get_source_units.return_value = parents
        result = DockerImporter()._import_images(self.conduit, units)
        self.assertEquals(result, units + parents)
        calls = [mock.call(u) for u in units]
        calls.extend([mock.call(u) for u in parents])
        self.conduit.associate_unit.assert_has_calls(calls)

    @mock.patch('pulp_docker.plugins.importers.importer.UnitAssociationCriteria')
    def test_import_manifests(self, criteria):
        layers = [
            {'blobSum': 'b2244'},
            {'blobSum': 'b2245'},
            {'blobSum': 'b2246'}
        ]
        units = [
            # ignored
            mock.Mock(type_id=models.Image.TYPE_ID),
            # manifests
            mock.Mock(
                type_id=models.Manifest.TYPE_ID,
                unit_key={'digest': 'A1234'},
                metadata={'fs_layers': []}
            ),
            mock.Mock(
                type_id=models.Manifest.TYPE_ID,
                unit_key={'digest': 'B1234'},
                metadata={'fs_layers': layers}
            ),
            mock.Mock(
                type_id=models.Manifest.TYPE_ID,
                unit_key={'digest': 'C1234'},
                metadata={'fs_layers': layers}
            ),
        ]

        conduit = mock.Mock()
        blobs = [dict(digest=l.values()[0]) for l in layers]
        conduit.get_source_units.return_value = blobs

        # test
        importer = DockerImporter()
        units_added = importer._import_manifests(conduit, units)

        # validation
        blob_filter = {
            'digest': {
                '$in': [l.values()[0] for l in layers]
            }
        }
        self.assertEqual(units_added, units[1:] + blobs)
        self.assertEqual(
            criteria.call_args_list,
            [
                mock.call(type_ids=[models.Blob.TYPE_ID], unit_filters=blob_filter),
            ])
        self.assertEqual(
            conduit.associate_unit.call_args_list,
            [
                mock.call(units[1]),
                mock.call(units[2]),
                mock.call(units[3]),
                mock.call(blobs[0]),
                mock.call(blobs[1]),
                mock.call(blobs[2]),
            ])

    def test_import_all_manifests(self):
        units = [
            mock.Mock(
                type_id=models.Manifest.TYPE_ID,
                unit_key={'digest': 'A1234'},
                metadata={'fs_layers': []}),
            mock.Mock(
                type_id=models.Manifest.TYPE_ID,
                unit_key={'digest': 'B1234'},
                metadata={'fs_layers': []}),
        ]
        conduit = mock.Mock()
        conduit.get_source_units.side_effect = [units, []]

        # test
        importer = DockerImporter()
        importer._import_manifests(conduit, None)

        # validation
        self.assertEqual(
            conduit.associate_unit.call_args_list,
            [
                mock.call(units[0]),
                mock.call(units[1]),
            ])


class TestValidateConfig(unittest.TestCase):
    def test_always_true(self):
        for repo, config in [['a', 'b'], [1, 2], [mock.Mock(), {}], ['abc', {'a': 2}]]:
            # make sure all attempts are validated
            self.assertEqual(DockerImporter().validate_config(repo, config), (True, ''))


class TestRemoveUnits(unittest.TestCase):

    @mock.patch(MODULE + '.DockerImporter._purge_unreferenced_tags')
    @mock.patch(MODULE + '.DockerImporter._purge_orphaned_blobs')
    def test_call(self, purge_blobs, purge_tags):
        repo = mock.Mock()
        config = mock.Mock()
        units = mock.Mock()
        importer = DockerImporter()
        importer.remove_units(repo, units, config)
        purge_tags.assert_called_once_with(repo, units)
        purge_blobs.assert_called_once_with(repo, units)


class TestPurgeUnreferencedTags(unittest.TestCase):

    def setUp(self):
        self.repo = Repository('repo_source')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})
        self.mock_unit = mock.Mock(
            type_id=models.Image.TYPE_ID, unit_key={'image_id': 'foo'}, metadata={})

    @mock.patch(MODULE + '.manager_factory.repo_manager')
    def test_remove_with_tag(self, mock_repo_manager):
        units = [
            # manifests
            mock.Mock(type_id=models.Manifest.TYPE_ID),
            # images
            mock.Mock(
                type_id=models.Image.TYPE_ID,
                unit_key={'image_id': 'foo'},
                metadata={}
            ),
        ]
        mock_repo_manager.return_value.get_repo_scratchpad.return_value = \
            {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                        constants.IMAGE_ID_KEY: 'foo'}]}
        DockerImporter()._purge_unreferenced_tags(self.repo, units)
        mock_repo_manager.return_value.set_repo_scratchpad.assert_called_once_with(
            self.repo.id, {u'tags': []}
        )

    @mock.patch(MODULE + '.manager_factory.repo_manager')
    def test_remove_without_tag(self, mock_repo_manager):
        expected_tags = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                    constants.IMAGE_ID_KEY: 'bar'}]}
        mock_repo_manager.return_value.get_repo_scratchpad.return_value = expected_tags

        DockerImporter()._purge_unreferenced_tags(self.repo, [self.mock_unit])
        mock_repo_manager.return_value.set_repo_scratchpad.assert_called_once_with(
            self.repo.id, expected_tags)


class TestPurgeOrphanedBlobs(unittest.TestCase):

    @mock.patch(MODULE + '.UnitAssociationCriteria')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_manager')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_query_manager')
    def test_purge_orphaned(self, query_manager, association_manager, criteria):
        repo = mock.Mock()
        blobs = [
            {'blobSum': 'blob-0'},  # manifest => 1
            {'blobSum': 'blob-1'},  # manifest => 1
            {'blobSum': 'blob-2'},  # manifest => 1
            {'blobSum': 'blob-3'},  # manifest => 1, 2, 3  (not orphaned)
            {'blobSum': 'blob-4'},  # manifest => 1, 2
            {'blobSum': 'blob-5'},  # manifest => 2, 4     (not orphaned)
            {'blobSum': 'blob-6'},  # manifest => 2
        ]
        removed = [
            mock.Mock(
                id='manifest-1',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs[0:4]}),
            mock.Mock(
                id='manifest-2',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs[2:8]})
        ]
        others = [
            mock.Mock(
                id='manifest-3',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs[3:4]}),
            mock.Mock(
                id='manifest-4',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs[5:6]})
        ]

        query_manager.return_value.get_units_by_type.return_value = others

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        criteria.assert_called_once_with(
            type_ids=[models.Blob.TYPE_ID],
            unit_filters={'digest': {'$in': ['blob-0', 'blob-1', 'blob-2', 'blob-4', 'blob-6']}})

        query_manager.return_value.get_units_by_type.assert_called_once_with(
            repo.id, models.Manifest.TYPE_ID)
        association_manager.return_value.unassociate_by_criteria(
            repo_id=repo.id,
            criteria=criteria.return_value,
            owner_type='',  # unused
            owner_id='',    # unused
            notify_plugins=False)

    @mock.patch(MODULE + '.UnitAssociationCriteria')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_manager')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_query_manager')
    def test_purge_orphaned_all_adopted(self, query_manager, association_manager, criteria):
        repo = mock.Mock()
        blobs = [
            {'blobSum': 'blob-0'},  # manifest => 1, 3     (not orphaned)
            {'blobSum': 'blob-1'},  # manifest => 1, 3     (not orphaned)
            {'blobSum': 'blob-2'},  # manifest => 1, 3     (not orphaned)
            {'blobSum': 'blob-3'},  # manifest => 1, 2, 3  (not orphaned)
            {'blobSum': 'blob-4'},  # manifest => 1, 2, 3  (not orphaned)
            {'blobSum': 'blob-5'},  # manifest => 2, 4, 3  (not orphaned)
            {'blobSum': 'blob-6'},  # manifest => 2, 3     (not orphaned)
        ]
        removed = [
            mock.Mock(
                id='manifest-1',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs[0:4]}),
            mock.Mock(
                id='manifest-2',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs[2:8]})
        ]
        others = [
            mock.Mock(
                id='manifest-3',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': blobs}),
        ]

        query_manager.return_value.get_units_by_type.return_value = others

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        self.assertFalse(criteria.called)
        self.assertFalse(association_manager.called)

    @mock.patch(MODULE + '.UnitAssociationCriteria')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_manager')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_query_manager')
    def test_purge_orphaned_nothing_orphaned(self, query_manager, association_manager, criteria):
        repo = mock.Mock()
        removed = [
            mock.Mock(
                id='manifest-1',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': []}),
            mock.Mock(
                id='manifest-2',
                type_id=models.Manifest.TYPE_ID,
                metadata={'fs_layers': []})
        ]

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        self.assertFalse(query_manager.called)
        self.assertFalse(criteria.called)
        self.assertFalse(association_manager.called)

    @mock.patch(MODULE + '.UnitAssociationCriteria')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_manager')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_query_manager')
    def test_purge_not_manifests(self, query_manager, association_manager, criteria):
        repo = mock.Mock()
        removed = [
            mock.Mock(type_id=models.Image.TYPE_ID),
            mock.Mock(type_id=models.Image.TYPE_ID),
        ]

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        self.assertFalse(query_manager.called)
        self.assertFalse(criteria.called)
        self.assertFalse(association_manager.called)
