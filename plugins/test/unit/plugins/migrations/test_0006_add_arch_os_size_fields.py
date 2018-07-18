import unittest

import mock

from pulp.server.db.migrate.models import _import_all_the_way


PATH_TO_MODULE = 'pulp_docker.plugins.migrations.0006_add_arch_os_size_fields'

migration = _import_all_the_way(PATH_TO_MODULE)


class TestMigrate(unittest.TestCase):
    """
    Test migration 0006.
    """

    def setUp(self):
        super(TestMigrate, self).setUp()
        self.manifest_list_need_migration = {
            '_id': '1',
            '_storage_path': '/dev/null',
            'manifests': ['hash1']
        }

        self.manifest_list_json = {
            'manifests': [
                {
                    'digest': 'hash1',
                    'platform': {
                        'os': 'linux',
                        'architecture': 'ppc64le'
                    }
                }]}

        self.manifest_need_migrations = {
            '_id': '1',
            'schema_version': 2,
            'fs_layers': [
                {'blob_sum': 'hash1'}
            ],
            '_storage_path': '/dev/null'
        }

        self.manifest_json = {
            'layers': [
                {
                    'size': 10,
                    'digest': 'hash1'
                }
            ]

        }

    @mock.patch('json.load')
    @mock.patch.object(migration, 'get_collection')
    def test_manifest_list_migration(self, mock_get_collection, mock_json):
        mock_json.return_value = self.manifest_list_json

        mock_get_collection.return_value.find.return_value.batch_size.return_value = [
            self.manifest_list_need_migration,
        ]
        migration.migrate_manifest_list()

        self.assertEqual(mock_get_collection.call_count, 1)

        mock_get_collection.return_value.update.assert_any_call(
            {'_id': self.manifest_list_need_migration['_id']},
            {'$set': {'manifests': [{'digest': 'hash1', 'os': 'linux', 'arch': 'ppc64le'}]}})

    @mock.patch('json.load')
    @mock.patch.object(migration, 'get_collection')
    def test_manifest_migration(self, mock_get_collection, mock_json):
        mock_json.return_value = self.manifest_json
        mock_get_collection.return_value.find.return_value.batch_size.return_value = [
            self.manifest_need_migrations,
        ]

        migration.migrate_manifest()

        self.assertEqual(mock_get_collection.call_count, 1)

        mock_get_collection.return_value.update.assert_any_call(
            {'_id': self.manifest_need_migrations['_id']},
            {'$set': {'fs_layers': [{'layer_type': None, 'blob_sum': 'hash1', 'size': 10}]}})
