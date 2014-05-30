from gettext import gettext as _


from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.extensions import PulpCliOption

from pulp_docker.common import constants, tarutils


d = _('image id of an ancestor image that should not be uploaded. '
      'The masked ancestor and any ancestors of that image will be skipped from the upload.')
OPT_MASK_ANCESTOR_ID = PulpCliOption('--mask-ancestor-id', d, required=False)


class UploadDockerImageCommand(UploadCommand):

    def __init__(self, context):
        super(UploadDockerImageCommand, self).__init__(context)
        self.add_option(OPT_MASK_ANCESTOR_ID)

    def determine_type_id(self, filename, **kwargs):
        """
        We only support one content type, so this always returns that.

        :return: ID of the type of file being uploaded
        :rtype:  str
        """
        return constants.IMAGE_TYPE_ID

    def generate_unit_key_and_metadata(self, filename, **kwargs):
        """
        Returns the unit key and metadata. This looks in the tarball and finds
        the layer that is not referenced as a parent to any other layer, in order
        to identify the ID of the image that is the leaf of the tree.

        :param filename: full path to the file being uploaded
        :type  filename: str, None

        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: tuple of unit key and metadata to upload for the file
        :rtype:  tuple
        """
        unit_key = {'image_id': tarutils.get_youngest_child(filename)}
        metadata = {}

        return unit_key, metadata
