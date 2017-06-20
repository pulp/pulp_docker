from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Remove tag and name fields from manifest collection.
    """

    tag = 'tag'
    name = 'name'
    collection = get_collection('units_docker_manifest')
    collection.update({tag: {"$exists": True}}, {"$unset": {tag: True}},
                      multi=True)
    collection.update({name: {"$exists": True}}, {"$unset": {name: True}},
                      multi=True)
