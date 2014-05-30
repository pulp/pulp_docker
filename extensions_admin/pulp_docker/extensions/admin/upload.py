from pulp.client.commands.repo.upload import UploadCommand

from pulp_docker.common import constants


class UploadDockerImageCommand(UploadCommand):
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
