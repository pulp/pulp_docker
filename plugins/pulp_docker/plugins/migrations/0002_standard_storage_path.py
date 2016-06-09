from pulp.server.db import connection

from pulp.plugins.migration.standard_storage_path import Migration, Plan, Unit


def migrate(*args, **kwargs):
    """
    Migrate content units to use the standard storage path introduced in pulp 2.8.
    """
    migration = Migration()
    migration.add(blob_plan())
    migration.add(ImagePlan())
    migration.add(manifest_plan())
    migration()


def blob_plan():
    """
    Factory to create a blob migration plan.

    :return: A configured plan.
    :rtype: Plan
    """
    key_fields = ('digest',)
    collection = connection.get_collection('units_docker_blob')
    return Plan(collection, key_fields)


def manifest_plan():
    """
    Factory to create a manifest migration plan.

    :return: A configured plan.
    :rtype: Plan
    """
    key_fields = ('digest',)
    collection = connection.get_collection('units_docker_manifest')
    return Plan(collection, key_fields)


class ImagePlan(Plan):
    """
    Migration plan for Image units.
    """

    def __init__(self):
        key_fields = ('image_id',)
        collection = connection.get_collection('units_docker_image')
        super(ImagePlan, self).__init__(collection, key_fields, join_leaf=False)

    def _new_unit(self, document):
        """
        Create a new unit for the specified document.
        Provides derived plan classes the opportunity to create specialized
        unit classes.

        :param document: A content unit document fetched from the DB.
        :type document: dict
        :return: A new unit.
        :rtype: ImageUnit
        """
        return ImageUnit(self, document)


class ImageUnit(Unit):
    """
    Docker image unit.
    """

    @property
    def files(self):
        """
        List of files (relative paths) associated with the unit.
        """
        return ['ancestry', 'json', 'layer']
