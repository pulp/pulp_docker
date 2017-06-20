import unittest

import mock

from pulp.server.db.migrate.models import _import_all_the_way


PATH_TO_MODULE = 'pulp_docker.plugins.migrations.0005_remove_manifest_unused_fields'

migration = _import_all_the_way(PATH_TO_MODULE)


class TestMigrate(unittest.TestCase):
    """
    Test migration 0005.
    """

    @mock.patch('.'.join((PATH_TO_MODULE, 'get_collection')))
    def test_migration(self, m_get_collection):
        # test
        migration.migrate()

        # validation
        m_get_collection.assert_called_once_with('units_docker_manifest')
        self.assertEqual(m_get_collection.return_value.update.call_count, 2)
        expected_calls = [
            mock.call({'tag': {'$exists': True}}, {'$unset': {'tag': True}}, multi=True),
            mock.call({'name': {'$exists': True}}, {'$unset': {'name': True}}, multi=True)
        ]
        m_get_collection.return_value.update.assert_has_calls(expected_calls)
