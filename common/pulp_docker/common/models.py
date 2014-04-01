class DockerImage(object):
    def __init__(self, image_id, parent_id, size):
        """
        :param image_id:    unique image ID
        :type  image_id:    basestring
        :param parent_id:   parent's unique image ID
        :type  parent_id:   basestring
        :param size:        size of the image in bytes
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