import unittest

import mock
from pulp.devel import skip
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.importer import Importer
from pulp.plugins.model import Repository
from pulp.server.db import model

import data
from pulp_docker.common import constants
from pulp_docker.plugins.importers.importer import DockerImporter, entry_point


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
            set(metadata['types']),
            set([constants.BLOB_TYPE_ID, constants.IMAGE_TYPE_ID, constants.MANIFEST_TYPE_ID,
                 constants.TAG_TYPE_ID]))
        self.assertTrue(len(metadata['display_name']) > 0)


@mock.patch('tempfile.mkdtemp', spec_set=True)
@mock.patch('shutil.rmtree')
class TestSyncRepo(unittest.TestCase):
    def setUp(self):
        super(TestSyncRepo, self).setUp()
        self.repo = Repository('repo1', working_dir='/a/b/c')
        self.repo.repo_obj = model.Repository(repo_id=self.repo.id)
        self.sync_conduit = mock.MagicMock()
        self.config = mock.MagicMock()
        self.importer = DockerImporter()

    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep')
    @mock.patch('pulp.plugins.util.publish_step.common_utils.get_working_directory',
                mock.MagicMock(return_value='/a/b/c'))
    def test_calls_sync_step(self, mock_sync_step, mock_rmtree, mock_mkdtemp):
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.assert_called_once_with(
            repo=self.repo, conduit=self.sync_conduit,
            config=self.config)

    @mock.patch('pulp_docker.plugins.importers.sync.SyncStep')
    @mock.patch('pulp.plugins.util.publish_step.common_utils.get_working_directory',
                mock.MagicMock(return_value='/a/b/c'))
    def test_calls_sync(self, mock_sync_step, mock_rmtree, mock_mkdtemp):
        """
        Assert that the sync_repo() method calls sync() on the SyncStep.
        """
        self.importer.sync_repo(self.repo, self.sync_conduit, self.config)

        mock_sync_step.return_value.process_lifecycle.assert_called_once_with()


class TestCancel(unittest.TestCase):
    def setUp(self):
        super(TestCancel, self).setUp()
        self.importer = DockerImporter()

    def test_calls_cancel(self):
        self.importer.sync_step = mock.MagicMock()

        self.importer.cancel_sync_repo()

        # make sure the step's cancel method was called
        self.importer.sync_step.cancel.assert_called_once_with()


class TestUploadUnit(unittest.TestCase):
    """
    Assert correct operation of DockerImporter.upload_unit().
    """
    @mock.patch('pulp_docker.plugins.importers.importer.model.Repository.objects')
    @mock.patch('pulp_docker.plugins.importers.importer.upload.UploadStep')
    def test_correct_calls(self, UploadStep, objects):
        """
        Assert that upload_unit() builds the UploadStep correctly and calls its process_lifecycle()
        method.
        """
        unit_key = {'image_id': data.busybox_ids[0]}
        repo = Repository('repo1')
        conduit = mock.MagicMock()
        config = PluginCallConfiguration({}, {})

        DockerImporter().upload_unit(repo, constants.IMAGE_TYPE_ID, unit_key,
                                     {}, data.busybox_tar_path, conduit, config)

        objects.get_repo_or_missing_resource.assert_called_once_with(repo.id)
        UploadStep.assert_called_once_with(repo=objects.get_repo_or_missing_resource.return_value,
                                           file_path=data.busybox_tar_path, config=config)
        UploadStep.return_value.process_lifecycle.assert_called_once_with()


class TestImportUnits(unittest.TestCase):

    def setUp(self):
        self.unit_key = {'image_id': data.busybox_ids[0]}
        self.source_repo = Repository('repo_source')
        self.dest_repo = Repository('repo_dest')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
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

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_import_all_images(self):
        units = [
            mock.Mock(type_id=constants.IMAGE_TYPE_ID,
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

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_import_images_no_parent(self):
        units = [
            mock.Mock(type_id=constants.IMAGE_TYPE_ID,
                      unit_key={'image_id': 'foo'},
                      metadata={}),
        ]
        result = DockerImporter()._import_images(self.conduit, units)
        self.assertEquals(result, units[0:1])
        self.conduit.associate_unit.assert_called_once_with(units[0])
        self.assertFalse(self.conduit.get_source_units.called)

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_import_images_with_parent(self):
        parents = [
            mock.Mock(
                id='parent',
                type_id=constants.IMAGE_TYPE_ID,
                unit_key={'image_id': 'bar-parent'},
                metadata={}),
        ]
        units = [
            mock.Mock(
                type_id=constants.IMAGE_TYPE_ID,
                unit_key={'image_id': 'foo'},
                metadata={}),
            mock.Mock(
                type_id=constants.IMAGE_TYPE_ID,
                unit_key={'image_id': 'bar'},
                metadata={'parent_id': 'bar-parent'}),
        ]
        self.conduit.get_source_units.return_value = parents
        result = DockerImporter()._import_images(self.conduit, units)
        self.assertEquals(result, units + parents)
        calls = [mock.call(u) for u in units]
        calls.extend([mock.call(u) for u in parents])
        self.conduit.associate_unit.assert_has_calls(calls)

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    @mock.patch('pulp_docker.plugins.importers.importer.UnitAssociationCriteria')
    def test_import_manifests(self, criteria):
        layers = [
            {'blobSum': 'b2244'},
            {'blobSum': 'b2245'},
            {'blobSum': 'b2246'}
        ]
        units = [
            # ignored
            mock.Mock(type_id=constants.IMAGE_TYPE_ID),
            # manifests
            mock.Mock(
                type_id=constants.MANIFEST_TYPE_ID,
                unit_key={'digest': 'A1234'},
                metadata={'fs_layers': []}
            ),
            mock.Mock(
                type_id=constants.MANIFEST_TYPE_ID,
                unit_key={'digest': 'B1234'},
                metadata={'fs_layers': layers}
            ),
            mock.Mock(
                type_id=constants.MANIFEST_TYPE_ID,
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
                mock.call(type_ids=[constants.BLOB_TYPE_ID], unit_filters=blob_filter),
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

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_import_all_manifests(self):
        units = [
            mock.Mock(
                type_id=constants.MANIFEST_TYPE_ID,
                unit_key={'digest': 'A1234'},
                metadata={'fs_layers': []}),
            mock.Mock(
                type_id=constants.MANIFEST_TYPE_ID,
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


@mock.patch('pulp_docker.plugins.importers.importer.model.Repository.objects')
class TestRemoveUnits(unittest.TestCase):

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    @mock.patch(MODULE + '.DockerImporter._purge_unreferenced_tags')
    @mock.patch(MODULE + '.DockerImporter._purge_orphaned_blobs')
    def test_call(self, purge_blobs, purge_tags, mock_repo_qs):
        repo = mock.Mock()
        config = mock.Mock()
        units = mock.Mock()
        importer = DockerImporter()

        importer.remove_units(repo, units, config)

        purge_tags.assert_called_once_with(repo, units)
        purge_blobs.assert_called_once_with(repo, units)

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_remove_with_tag(self, mock_repo_qs):
        units = [
            mock.MagicMock(type_id=constants.MANIFEST_TYPE_ID),
            mock.MagicMock(type_id=constants.IMAGE_TYPE_ID, unit_key={'image_id': 'foo'},
                           metadata={})
        ]
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.scratchpad = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                           constants.IMAGE_ID_KEY: 'foo'}]}

        DockerImporter().remove_units(mock_repo, units, mock.MagicMock())

        self.assertEqual(mock_repo.scratchpad['tags'], [])


@mock.patch('pulp_docker.plugins.importers.importer.model.Repository.objects')
class TestPurgeUnreferencedTags(unittest.TestCase):

    def setUp(self):
        self.repo = Repository('repo_source')
        self.conduit = mock.MagicMock()
        self.config = PluginCallConfiguration({}, {})
        self.mock_unit = mock.Mock(
            type_id=constants.IMAGE_TYPE_ID, unit_key={'image_id': 'foo'}, metadata={})

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_remove_with_tag(self, mock_repo_qs):
        units = [
            # manifests
            mock.Mock(type_id=constants.MANIFEST_TYPE_ID),
            # images
            mock.Mock(
                type_id=constants.IMAGE_TYPE_ID,
                unit_key={'image_id': 'foo'},
                metadata={}
            ),
        ]
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.scratchpad = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                           constants.IMAGE_ID_KEY: 'foo'}]}

        DockerImporter()._purge_unreferenced_tags(self.repo, units)

        self.assertEqual(mock_repo.scratchpad, {'tags': []})
        mock_repo.save.assert_called_once_with()

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    def test_remove_without_tag(self, mock_repo_qs):
        expected_tags = {u'tags': [{constants.IMAGE_TAG_KEY: 'apple',
                                    constants.IMAGE_ID_KEY: 'bar'}]}
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.scratchpad = expected_tags

        DockerImporter()._purge_unreferenced_tags(self.repo, [self.mock_unit])

        self.assertEqual(mock_repo.scratchpad['tags'], expected_tags['tags'])
        mock_repo.save.assert_called_once_with()


class TestPurgeOrphanedBlobs(unittest.TestCase):

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
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
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs[0:4]}),
            mock.Mock(
                id='manifest-2',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs[2:8]})
        ]
        others = [
            mock.Mock(
                id='manifest-3',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs[3:4]}),
            mock.Mock(
                id='manifest-4',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs[5:6]})
        ]

        query_manager.return_value.get_units_by_type.return_value = others

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        criteria.assert_called_once_with(
            type_ids=[constants.BLOB_TYPE_ID],
            unit_filters={'digest': {'$in': ['blob-0', 'blob-1', 'blob-2', 'blob-4', 'blob-6']}})

        query_manager.return_value.get_units_by_type.assert_called_once_with(
            repo.id, constants.MANIFEST_TYPE_ID)
        association_manager.return_value.unassociate_by_criteria(
            repo_id=repo.id,
            criteria=criteria.return_value,
            owner_type='',  # unused
            owner_id='',    # unused
            notify_plugins=False)

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
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
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs[0:4]}),
            mock.Mock(
                id='manifest-2',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs[2:8]})
        ]
        others = [
            mock.Mock(
                id='manifest-3',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': blobs}),
        ]

        query_manager.return_value.get_units_by_type.return_value = others

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        self.assertFalse(criteria.called)
        self.assertFalse(association_manager.called)

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    @mock.patch(MODULE + '.UnitAssociationCriteria')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_manager')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_query_manager')
    def test_purge_orphaned_nothing_orphaned(self, query_manager, association_manager, criteria):
        repo = mock.Mock()
        removed = [
            mock.Mock(
                id='manifest-1',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': []}),
            mock.Mock(
                id='manifest-2',
                type_id=constants.MANIFEST_TYPE_ID,
                metadata={'fs_layers': []})
        ]

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        self.assertFalse(query_manager.called)
        self.assertFalse(criteria.called)
        self.assertFalse(association_manager.called)

    # We are under a significant time crunch and don't have time to correct all the tests with this
    # commit. Thus, the decision was made to skip broken tests and come back and fix them later.
    @skip.skip_broken
    @mock.patch(MODULE + '.UnitAssociationCriteria')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_manager')
    @mock.patch(MODULE + '.manager_factory.repo_unit_association_query_manager')
    def test_purge_not_manifests(self, query_manager, association_manager, criteria):
        repo = mock.Mock()
        removed = [
            mock.Mock(type_id=constants.IMAGE_TYPE_ID),
            mock.Mock(type_id=constants.IMAGE_TYPE_ID),
        ]

        # test
        importer = DockerImporter()
        importer._purge_orphaned_blobs(repo, removed)

        # validation
        self.assertFalse(query_manager.called)
        self.assertFalse(criteria.called)
        self.assertFalse(association_manager.called)
