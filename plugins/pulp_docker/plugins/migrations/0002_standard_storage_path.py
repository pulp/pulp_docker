from pulp.server.db import connection

from pulp.plugins.migration.standard_storage_path import Migration, Plan


def migrate(*args, **kwargs):
    """
    Migrate content units to use the standard storage path introduced in pulp 2.8.
    """
    migration = Migration()
    migration.add(blob_plan())
    migration.add(image_plan())
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


def image_plan():
    """
    Factory to create an image migration plan.

    :return: A configured plan.
    :rtype: Plan
    """
    key_fields = ('image_id',)
    collection = connection.get_collection('units_docker_image')
    return Plan(collection, key_fields, join_leaf=False)


def manifest_plan():
    """
    Factory to create a manifest migration plan.

    :return: A configured plan.
    :rtype: Plan
    """
    key_fields = ('digest',)
    collection = connection.get_collection('units_docker_manifest')
    return Plan(collection, key_fields)
