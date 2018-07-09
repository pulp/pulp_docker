import json
import logging

from pulp.server.db.connection import get_collection
from pulp.server.db.migrations.lib import utils


_logger = logging.getLogger('pulp_docjer.plugins.migrations.0006')


def migrate(*args, **kwargs):
    migrate_manifest_list()
    migrate_manifest()


def migrate_manifest_list():
    """
    Update format of manifest on manifest lists to have digest, os, and arch fields
    """

    manifest_list_collection = get_collection('units_docker_manifest_list')
    total_manifest_lists = manifest_list_collection.count(
        {'manifests': {'$type': 2}})

    with utils.MigrationProgressLog('Update manifest field on ManifestList',
                                    total_manifest_lists) as migration_log:
        for manifest_list in manifest_list_collection.find(
                {'manifests': {'$type': 2}}).batch_size(100):

            with open(manifest_list['_storage_path']) as fd:
                manifest_list_json = json.load(fd)

            manifests = []
            for manifest in manifest_list_json['manifests']:

                manifest = {'digest': manifest['digest'],
                            'os': manifest.get('platform', {}).get('os', ''),
                            'arch': manifest.get('platform', {}).get('architecture', '')}
                manifests.append(manifest)

            manifest_list_collection.update(
                {'_id': manifest_list['_id']},
                {'$set': {'manifests': manifests}})
            migration_log.progress()


def migrate_manifest():
    """
    Add size field to fslayers in schema2 manifest.
    Only do this for schema2 manifests, since schema1 does not store size in manifest.json
    """
    manifest_collection = get_collection('units_docker_manifest')

    total_manifests = manifest_collection.count({
        'fs_layers.size': {'$exists': False},
        'schema_version': {'$eq': 2}})

    with utils.MigrationProgressLog('Update manifest.fs_layers.size',
                                    total_manifests) as migration_log:

        for manifest in manifest_collection.find(
                {'fs_layers.size': {'$exists': False},
                 'schema_version': {'$eq': 2}}).batch_size(100):

            with open(manifest['_storage_path']) as fd:
                manifest_json = json.load(fd)

            fs_layers = []
            for layer in manifest_json['layers']:
                fs_layer = {
                    'blob_sum': layer['digest'],
                    'layer_type': layer.get('mediaType', None),
                    'size': layer.get('size', '')
                }

                fs_layers.append(fs_layer)

            manifest_collection.update(
                {'_id': manifest['_id']},
                {'$set': {'fs_layers': fs_layers}}
            )

            migration_log.progress()
