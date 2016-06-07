from unittest import TestCase

from mock import patch, Mock

from pulp.server.db.migrate.models import _import_all_the_way


PATH_TO_MODULE = 'pulp_docker.plugins.migrations.0002_standard_storage_path'

migration = _import_all_the_way(PATH_TO_MODULE)


class TestMigrate(TestCase):
    """
    Test migration 0002.
    """

    @patch(PATH_TO_MODULE + '.manifest_plan')
    @patch(PATH_TO_MODULE + '.ImagePlan')
    @patch(PATH_TO_MODULE + '.blob_plan')
    @patch(PATH_TO_MODULE + '.Migration')
    def test_migrate(self, _migration, *functions):
        plans = []
        _migration.return_value.add.side_effect = plans.append

        # test
        migration.migrate()

        # validation
        self.assertEqual(
            plans,
            [
                f.return_value for f in functions
            ])
        _migration.return_value.assert_called_once_with()


class TestPlans(TestCase):

    @patch(PATH_TO_MODULE + '.connection.get_collection')
    def test_blob(self, get_collection):
        # test
        plan = migration.blob_plan()

        # validation
        get_collection.assert_called_once_with('units_docker_blob')
        self.assertEqual(plan.collection, get_collection.return_value)
        self.assertEqual(plan.key_fields, ('digest',))
        self.assertTrue(plan.join_leaf)
        self.assertTrue(isinstance(plan, migration.Plan))

    @patch(PATH_TO_MODULE + '.connection.get_collection')
    def test_manifest(self, get_collection):
        # test
        plan = migration.manifest_plan()

        # validation
        get_collection.assert_called_once_with('units_docker_manifest')
        self.assertEqual(plan.collection, get_collection.return_value)
        self.assertEqual(plan.key_fields, ('digest',))
        self.assertTrue(plan.join_leaf)
        self.assertTrue(isinstance(plan, migration.Plan))


class TestImagePlan(TestCase):

    @patch(PATH_TO_MODULE + '.connection.get_collection')
    def test_init(self, get_collection):
        # test
        plan = migration.ImagePlan()

        # validation
        get_collection.assert_called_once_with('units_docker_image')
        self.assertEqual(plan.collection, get_collection.return_value)
        self.assertEqual(plan.key_fields, ('image_id',))
        self.assertFalse(plan.join_leaf)
        self.assertTrue(isinstance(plan, migration.Plan))

    @patch(PATH_TO_MODULE + '.connection.get_collection')
    def test_new_unit(self, get_collection):
        document = {'A': 1}
        # test
        plan = migration.ImagePlan()
        unit = plan._new_unit(document)

        # validation
        self.assertEqual(unit.document, document)
        self.assertTrue(unit, migration.ImageUnit)


class TestImageUnit(TestCase):

    def test_files(self):
        unit = migration.ImageUnit(Mock(), {})
        self.assertEqual(unit.files, ['ancestry', 'json', 'layer'])
