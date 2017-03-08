from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Add schema_version to the tag collection.
    """

    schema_version_key = 'schema_version'
    collection = get_collection('units_docker_tag')
    # drop old index due to unit_keys fields change
    index_info = collection.index_information()
    old_index = 'name_1_repo_id_1'
    if old_index in index_info:
        collection.drop_index(old_index)
    # update collection with new field
    for tag in collection.find():
        if schema_version_key not in tag.keys():
            tag[schema_version_key] = 1
            collection.save(tag)
