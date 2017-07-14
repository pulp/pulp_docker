"""
This module contains tests for pulp_docker.plugins.migrations.0004_tag_schema_change.py
"""
from unittest import TestCase

from mock import Mock, patch, call

from pulp.server.db.migrate.models import _import_all_the_way


PATH_TO_MODULE = 'pulp_docker.plugins.migrations.0004_tag_schema_change'

migration = _import_all_the_way(PATH_TO_MODULE)

MANIFEST_TYPE = 'manifest_type'


class TestMigration(TestCase):
    """
    Test the migration.
    """

    @patch('.'.join((PATH_TO_MODULE, 'get_collection')))
    def test_migrate(self, m_get_collection):
        """
        Test manifest_type field added and collection index dropped.
        """
        collection = Mock()
        collection.index_information.return_value = ['name_1_repo_id_1_schema_version_1']
        m_get_collection.return_value = collection

        # test
        migration.migrate()

        # validation
        collection.drop_index.assert_called_once_with('name_1_repo_id_1_schema_version_1')
        m_get_collection.assert_called_once_with('units_docker_tag')
        self.assertEqual(m_get_collection.return_value.update.call_count, 1)
        expected_call = [
            call({MANIFEST_TYPE: {'$exists': False}}, {'$set': {MANIFEST_TYPE: 'image'}},
                 multi=True),
        ]
        m_get_collection.return_value.update.assert_has_calls(expected_call)
