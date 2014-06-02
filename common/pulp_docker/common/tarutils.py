import contextlib
import json
import os
import tarfile


def get_metadata(tarfile_path):
    """
    Given a path to a tarfile, which is itself the product of "docker save",
    this discovers what images (layers) exist in the archive and returns
    metadata about each.

    Current fields in metadata:
        parent: ID of the parent image, or None if there is none
        size:   size in bytes as reported by docker

    :param tarfile_path:    full path to a tarfile that is the product
                            of "docker save"
    :type  tarfile_path:    basestring

    :return:    A dictionary where keys are image IDs, and values are
                dictionaries that contain the above-described metadata.
    :rtype:     dict
    """
    metadata = {}

    with contextlib.closing(tarfile.open(tarfile_path)) as archive:
        for member in archive.getmembers():
            # find the "json" files, which contain all image metadata
            if os.path.basename(member.path) == 'json':
                image_data = json.load(archive.extractfile(member))
                metadata[image_data['id']] = {
                    'parent': image_data.get('parent'),
                    'size': image_data['Size']
                }

    return metadata


def get_tags(tarfile_path):
    """
    returns a dictionary of docker tags, retrieved from the tarfile

    :param tarfile_path:    full path to the tarfile
    :type  tarfile_path:    basestring
    """
    with contextlib.closing(tarfile.open(tarfile_path)) as archive:
        repo_file = archive.extractfile('repositories')
        repo_json = json.load(repo_file)

    if len(repo_json) != 1:
        raise ValueError('pulp only supports one repo per tarfile')

    return repo_json.popitem()[1]


def get_ancestry(image_id, metadata):
    """
    Given an image ID and metadata about each image, this calculates and returns
    the ancestry list for that image. It walks the "parent" relationship in the
    metadata to assemble the list, which is ordered with the child leaf at the
    top.

    :param image_id:    unique ID for a docker image
    :type  image_id:    basestring
    :param metadata:    A dictionary where keys are image IDs, and values are
                        dictionaries that contain a key 'parent' with the ID
                        of a docker image
    :type  metadata     dict

    :return:    a tuple of image IDs where the first is the image_id passed in,
                and each successive ID is the parent image of the ID that
                proceeds it.
    :rtype:     tuple
    """
    image_ids = []

    while image_id:
        image_ids.append(image_id)
        image_id = metadata[image_id].get('parent')

    return tuple(image_ids)


def get_youngest_children(metadata):
    """
    Given a full path to a tarfile, figure out which image IDs are leaf nodes,
    aka the youngest children.

    :param metadata:    a dictionary where keys are image IDs, and values are
                        dictionaries with keys "parent" and "size", containing
                        values for those two attributes as taken from the docker
                        image metadata.
    :type  metadata:    dict

    :return:    image IDs for the youngest docker images
    :rtype:     list
    """
    image_ids = set(metadata.keys())
    for image_data in metadata.values():
        parent = image_data.get('parent')
        if parent is not None:
            try:
                image_ids.remove(parent)
            except KeyError:
                # This can happen if an image is a parent of multiple child images,
                # in which case this could be already removed from image_ids.
                pass

    return list(image_ids)
