import contextlib
import functools
import gzip
import json
import os
import tarfile

from pulp.server.managers import factory

from pulp_docker.common import models, tarutils


def get_models(metadata, unit_key, mask_id=''):
    """
    Given some metadata and a unit key, returns model instances to represent
    each layer of the image defined by the unit_key

    :param metadata:    a dictionary where keys are image IDs, and values are
                        dictionaries with keys "parent" and "size", containing
                        values for those two attributes as taken from the docker
                        image metadata.
    :type  metadata:    dict
    :param unit_key:    a dictionary containing the unit key of the youngest
                        child docker image
    :type  unit_key:    dict
    :param mask_id:     The ID of an image that should not be included in the
                        returned models. This image and all of its ancestors
                        will be excluded.
    :type  mask_id:     basestring

    :return:    list of models.DockerImage instances
    :rtype:     list
    """
    images = []

    image_id = unit_key['image_id']
    while image_id:
        json_data = metadata[image_id]
        parent_id = json_data.get('parent')
        size = json_data['size']

        images.append(models.DockerImage(image_id, parent_id, size))

        if parent_id == mask_id:
            break

        image_id = parent_id

    return images


def save_models(conduit, models, ancestry, tarfile_path):
    """
    Given a collection of models, save them to pulp as Units.

    :param conduit:         the conduit provided by pulp
    :type  conduit:         pulp.plugins.conduits.unit_add.UnitAddConduit
    :param models:          collection of models.DockerImage instances to save
    :type  models:          list
    :param ancestry:        a tuple of image IDs where the first is the image_id
                            passed in, and each successive ID is the parent image of
                            the ID that proceeds it.
    :type  ancestry:        tuple
    :param tarfile_path:    full path to a tarfile that is the product
                            of "docker save"
    :type  tarfile_path:    basestring
    """
    with contextlib.closing(tarfile.open(tarfile_path)) as archive:
        for i, model in enumerate(models):
            unit = conduit.init_unit(model.TYPE_ID, model.unit_key,
                                     model.unit_metadata, model.relative_path)

            # skip saving files if they already exist, which could happen if the
            # unit already existed in pulp
            if not os.path.exists(unit.storage_path):
                os.makedirs(unit.storage_path, 0755)

                # save ancestry file
                json.dump(ancestry[i:], open(os.path.join(unit.storage_path, 'ancestry'), 'w'))
                # save json file
                json_src_path = os.path.join(model.image_id, 'json')
                with open(os.path.join(unit.storage_path, 'json'), 'w') as json_dest:
                    json_dest.write(archive.extractfile(json_src_path).read())
                # save layer file
                layer_src_path = os.path.join(model.image_id, 'layer.tar')
                layer_dest_path = os.path.join(unit.storage_path, 'layer')
                with contextlib.closing(archive.extractfile(layer_src_path)) as layer_src:
                    with contextlib.closing(gzip.open(layer_dest_path, 'w')) as layer_dest:
                        # these can be big files, so we chunk them
                        reader = functools.partial(layer_src.read, 4096)
                        for chunk in iter(reader, ''):
                            layer_dest.write(chunk)

            conduit.save_unit(unit)


def update_tags(repo_id, tarfile_path):
    """
    Gets the current scratchpad's tags and updates them with the tags contained
    in the tarfile.

    :param repo_id:         unique ID of a repository
    :type  repo_id:         basestring
    :param tarfile_path:    full path to a tarfile that is the product
                            of "docker save"
    :type  tarfile_path:    basestring
    """
    repo_manager = factory.repo_manager()
    new_tags = tarutils.get_tags(tarfile_path)

    scratchpad = repo_manager.get_repo_scratchpad(repo_id)
    tags = scratchpad.get('tags', {})
    tags.update(new_tags)
    repo_manager.update_repo_scratchpad(repo_id, {'tags': tags})
