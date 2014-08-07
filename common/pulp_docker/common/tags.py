from pulp_docker.common import constants


def generate_updated_tags(scratchpad, new_tags):
    """
    Get the current repo scratchpad's tags and generate an updated tag list
    by adding new tags to them. If a tag exists on the scratchpad as well as
    in the new tags, the old tag will be overwritten by the new tag.

    :param scratchpad: repo scratchpad dictionary
    :type  scratchpad: dict
    :param new_tags:   dictionary of tag:image_id
    :type  new_tags:   dict
    :return:           list of dictionaries each containing values for 'tag' and 'image_id' keys
    :rtype:            list of dict
    """
    tags = scratchpad.get('tags', [])

    # Remove common tags between existing and new tags so we don't have duplicates
    for tag_dict in tags[:]:
        if tag_dict[constants.IMAGE_TAG_KEY] in new_tags.keys():
            tags.remove(tag_dict)
    # Add new tags to existing tags. Since tags can contain '.' which cannot be stored
    # as a key in mongodb, we are storing them this way.
    for tag, image_id in new_tags.items():
        tags.append({constants.IMAGE_TAG_KEY: tag, constants.IMAGE_ID_KEY: image_id})

    return tags
