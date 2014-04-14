import os

from pulp_docker.common import constants


class DockerImage(object):
    TYPE_ID = constants.IMAGE_TYPE_ID

    def __init__(self, image_id, parent_id, size):
        """
        :param image_id:    unique image ID
        :type  image_id:    basestring
        :param parent_id:   parent's unique image ID
        :type  parent_id:   basestring
        :param size:        size of the image in bytes, as reported by docker
        :type  size:        int
        """
        self.image_id = image_id
        self.parent_id = parent_id
        self.size = size

    @property
    def unit_key(self):
        """
        :return:    unit key
        :rtype:     dict
        """
        return {
            'image_id': self.image_id
        }

    @property
    def relative_path(self):
        """
        :return:    the relative path to where this image's directory should live
        :rtype:     basestring
        """
        return os.path.join(self.TYPE_ID, self.image_id)

    @property
    def unit_metadata(self):
        """
        :return:    a subset of the complete docker metadata about this image,
                    including only what pulp_docker cares about
        :rtype:     dict
        """
        return {
            'parent_id': self.parent_id,
            'size': self.size
        }
