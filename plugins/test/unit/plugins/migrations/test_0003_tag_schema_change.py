"""
This module contains tests for pulp_docker.plugins.migrations.0003_tag_schema_change.py
"""
from copy import deepcopy
from unittest import TestCase

from mock import Mock, patch

from pulp.server.db.migrate.models import _import_all_the_way


PATH_TO_MODULE = 'pulp_docker.plugins.migrations.0003_tag_schema_change'

migration = _import_all_the_way(PATH_TO_MODULE)

SCHEMA_VERSION = 'schema_version'


class TestMigration(TestCase):
    """
    Test the migration.
    """

    @patch('.'.join((PATH_TO_MODULE, 'get_collection')))
    def test_migrate(self, m_get_collection):
        """
        Test schema_version field added and collection index dropped.
        """
        collection = Mock()
        found = [
            {SCHEMA_VERSION: 1}, {}, {SCHEMA_VERSION: 2}
        ]
        collection.find.return_value = deepcopy(found)
        collection.index_information.return_value = ['name_1_repo_id_1']
        m_get_collection.return_value = collection

        # test
        migration.migrate()

        # validation
        collection.drop_index.assert_called_once_with('name_1_repo_id_1')
        collection.find.assert_called_once_with()
        m_get_collection.assert_called_once_with('units_docker_tag')
        self.assertTrue(SCHEMA_VERSION in tags for tags in collection.save.call_args_list)
        self.assertEqual(len(collection.save.call_args_list), 1)
