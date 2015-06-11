from pulp.server.db import model

from pulp_docker.common import tags


def update_tags(repo_id, new_tags):
    """
    Gets the current scratchpad's tags and updates them with the new_tags

    :param repo_id:     unique ID of a repository
    :type  repo_id:     basestring
    :param new_tags:    dictionary of tag:image_id
    :type  new_tags:    dict
    """
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    new_tags = tags.generate_updated_tags(repo_obj.scratchpad, new_tags)
    repo_obj.scratchpad['tags'] = new_tags
    repo_obj.save()
