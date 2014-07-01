from pulp.server.managers import factory
from pulp_docker.common import tags


def update_tags(repo_id, new_tags):
    """
    Gets the current scratchpad's tags and updates them with the new_tags

    :param repo_id:     unique ID of a repository
    :type  repo_id:     basestring
    :param new_tags:    dictionary of tag:image_id
    :type  new_tags:    dict
    """
    repo_manager = factory.repo_manager()
    scratchpad = repo_manager.get_repo_scratchpad(repo_id)
    new_tags = tags.generate_updated_tags(scratchpad, new_tags)
    repo_manager.update_repo_scratchpad(repo_id, {'tags': new_tags})
