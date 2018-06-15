from gettext import gettext as _
import json
import tarfile

from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.extensions import PulpCliOption
from pulp.client.commands import options as std_options

from pulp_docker.common import constants, tarutils


d = _('image id of an ancestor image that should not be added to the repository. '
      'The masked ancestor and any ancestors of that image will be skipped from importing into '
      'the repository. This option applies only to docker v1 uploads.')
OPT_MASK_ANCESTOR_ID = PulpCliOption('--mask-id', d, aliases=['-m'], required=False)

d = _('name of the tag to create  or update')
TAG_NAME_OPTION = PulpCliOption('--tag-name', d)

d = _('digest of the image manifest or manifest list (e.g. sha256:3e006...)')
DIGEST_OPTION = PulpCliOption('--digest', d)

DESC_UPDATE_TAGS = _('create or update a tag to point to a manifest')


class UploadDockerImageCommand(UploadCommand):

    def __init__(self, context):
        super(UploadDockerImageCommand, self).__init__(context)
        self.add_option(OPT_MASK_ANCESTOR_ID)

    def determine_type_id(self, filename, **kwargs):
        """
        Determine type id of the upload file by file type.

        json -> Manifest List
        tarfile -> V1 Image or V2 Image Manifest

        :return: ID of the type of file being uploaded
        :rtype:  str
        :raises: RuntimeError if file is not a valid tarfile or json file.
        """

        try:
            image_manifest = tarutils.get_image_manifest(filename)
        except tarfile.ReadError:
            pass
        else:
            if isinstance(image_manifest, list):
                return constants.IMAGE_TYPE_ID
            else:
                return constants.MANIFEST_TYPE_ID

        try:
            with open(filename) as upload:
                json.load(upload)
            return constants.MANIFEST_LIST_TYPE_ID
        except ValueError:
            raise RuntimeError(
                _("Upload file could not be processed. Manifest Lists must be valid JSON, "
                  "Images (V1 and V2) must be tarfiles."))

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
        if OPT_MASK_ANCESTOR_ID.keyword in kwargs and kwargs.get(OPT_MASK_ANCESTOR_ID.keyword):
            override_config[constants.CONFIG_KEY_MASK_ID] = kwargs[OPT_MASK_ANCESTOR_ID.keyword]

        return override_config


class TagUpdateCommand(UploadCommand):
    """
    Command used to point a tag to a particular manifest. This will either
    update an existing tag or create a new tag if one does not exist
    """

    def __init__(self, context):
        super(TagUpdateCommand, self).__init__(context, name='tag',
                                               upload_files=False,
                                               description=DESC_UPDATE_TAGS)
        self.add_option(TAG_NAME_OPTION)
        self.add_option(DIGEST_OPTION)

    def determine_type_id(self, filename, **kwargs):
        """
        Returns the ID of the type of file being uploaded.

        :param filename: full path to the file being uploaded
        :type  filename: str
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: ID of the type of file being uploaded
        :rtype:  str
        """

        return constants.TAG_TYPE_ID

    def generate_unit_key(self, filename, **kwargs):
        """
        Returns the unit key that should be specified in the upload request.

        :param filename: full path to the file being uploaded
        :type  filename: str, None
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: unit key that should be uploaded for the file
        :rtype:  dict
        """

        tag_name = kwargs[TAG_NAME_OPTION.keyword]
        repo_id = kwargs[std_options.OPTION_REPO_ID.keyword]

        return {'name': tag_name, 'repo_id': repo_id}

    def generate_metadata(self, filename, **kwargs):
        """
        Returns a dictionary of metadata that should be included
        as part of the upload request.

        :param filename: full path to the file being uploaded
        :type  filename: str, None
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: metadata information that should be uploaded for the file
        :rtype:  dict
        """

        tag_name = kwargs[TAG_NAME_OPTION.keyword]
        digest = kwargs[DIGEST_OPTION.keyword]

        return {'name': tag_name, 'digest': digest}
