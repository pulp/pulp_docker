from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Add manifest_type to the tag collection.
    """
    image = 'image'
    manifest_type_key = 'manifest_type'
    collection = get_collection('units_docker_tag')
    # drop old index due to unit_keys fields change
    index_info = collection.index_information()
    old_index = 'name_1_repo_id_1_schema_version_1'
    if old_index in index_info:
        collection.drop_index(old_index)
    # update collection with new field
    collection.update({manifest_type_key: {'$exists': False}},
                      {'$set': {manifest_type_key: image}}, multi=True)
