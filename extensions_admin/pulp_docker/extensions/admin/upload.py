from gettext import gettext as _


from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.extensions import PulpCliOption

from pulp_docker.common import constants


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
        Returns unit key and metadata as empty dictionaries. This is appropriate
        in this case, since docker image consists of multiple layers each having
        it's own unit key and each layer is imported separately into the server database.

        :param filename: full path to the file being uploaded
        :type  filename: str, None

        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: tuple of unit key and metadata to upload for the file
        :rtype:  tuple
        """
        unit_key = {}
        metadata = {}

        return unit_key, metadata

    def generate_override_config(self, **kwargs):
        """
        Generate an override config value to the upload command.

        :param kwargs: parsed from the user input
        :type kwargs:  dict

        :return: override config generated from the user input
        :rtype:  dict
        """
        override_config = {}

        if OPT_MASK_ANCESTOR_ID.keyword in kwargs:
            override_config[constants.CONFIG_KEY_MASK_ID] = kwargs[OPT_MASK_ANCESTOR_ID.keyword]

        return override_config
