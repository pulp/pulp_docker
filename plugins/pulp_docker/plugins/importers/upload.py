import contextlib
from gettext import gettext as _
import json
import os
import stat
import tarfile

from pulp.plugins.util.publish_step import PluginStep, GetLocalUnitsStep

from pulp_docker.common import constants, tarutils
from pulp_docker.plugins.db import models
from pulp_docker.plugins.importers import sync


class UploadStep(PluginStep):

    def __init__(self, repo=None, file_path=None, config=None):
        """
        :param repo: repository to sync
        :type  repo:  pulp.plugins.model.Repository
        :param file_path: The path to the tar file uploaded from a 'docker save'
        :type file_path: str
        """
        super(UploadStep, self).__init__(constants.UPLOAD_STEP, repo=repo,
                                         plugin_type=constants.IMPORTER_TYPE_ID,
                                         config=config, disable_reporting=True)
        self.description = _('Uploading Docker Units')

        self.file_path = file_path

        # populated by ProcessMetadata
        self.metadata = None

        # Units that were part of the uploaded tar file, populated by ProcessMetadata
        self.available_units = []

        # populated by ProcessMetadata
        self.tags = {}

        self.add_child(ProcessMetadata(self.file_path))
        # save this step so its "units_to_download" attribute can be accessed later
        self.step_get_local_units = GetLocalUnitsStep(constants.IMPORTER_TYPE_ID)
        self.add_child(self.step_get_local_units)
        self.add_child(AddDockerUnits(tarfile_path=self.file_path))


class ProcessMetadata(PluginStep):
    """
    Retrieve metadata from an uploaded tarball and pull out the
    metadata for further processing
    """

    def __init__(self, file_path, **kwargs):
        """
        :param file_path: The path to the tar uploaded tar file from "docker save..."
        :type file_path: str
        """
        super(ProcessMetadata, self).__init__(constants.UPLOAD_STEP_METADATA)
        self.file_path = file_path

    def process_main(self, item=None):
        """
        Pull the metadata out of the tar file

        :param item: Not used by this Step
        :type item: None
        """

        # retrieve metadata from the tarball
        metadata = tarutils.get_metadata(self.file_path)
        # turn that metadata into a collection of models
        mask_id = self.get_config().get(constants.CONFIG_KEY_MASK_ID)
        self.parent.metadata = metadata
        self.parent.available_units = self.get_models(metadata, mask_id)
        self.parent.tags = tarutils.get_tags(self.file_path)

    def get_models(self, metadata, mask_id=''):
        """
        Given image metadata, returns model instances to represent
        each layer of the image defined by the unit_key

        :param metadata:    a dictionary where keys are image IDs, and values are
                            dictionaries with keys "parent" and "size", containing
                            values for those two attributes as taken from the docker
                            image metadata.
        :type  metadata:    dict
        :param mask_id:     The ID of an image that should not be included in the
                            returned models. This image and all of its ancestors
                            will be excluded.
        :type  mask_id:     basestring

        :return:    list of models.DockerImage instances
        :rtype:     list
        """
        images = []
        existing_image_ids = set()

        leaf_image_ids = tarutils.get_youngest_children(metadata)

        for image_id in leaf_image_ids:
            while image_id:
                json_data = metadata[image_id]
                parent_id = json_data.get('parent')
                size = json_data['size']

                if image_id not in existing_image_ids:
                    # This will avoid adding multiple images with a same id, which can happen
                    # in case of parents with multiple children.
                    existing_image_ids.add(image_id)
                    images.append(models.DockerImage(image_id=image_id,
                                                     parent_id=parent_id,
                                                     size=size))
                if parent_id == mask_id:
                    break
                image_id = parent_id

        return images


class AddDockerUnits(sync.SaveDockerUnits):
    """
    Add docker units from metadata extracted in the ProcessMetadata step
    """

    def __init__(self, tarfile_path=None):
        """
        :param tarfile_path: The path to the tar uploaded tar file from "docker save..."
        :type tarfile_path: str
        """

        self.model_class = models.DockerImage
        super(AddDockerUnits, self).__init__(step_type=constants.UPLOAD_STEP_SAVE)
        self.tarfile_path = tarfile_path

    def initialize(self):
        """
        Extract the tarfile to get all the layers from it
        """
        # Brute force, extract the tar file for now
        with contextlib.closing(tarfile.open(self.tarfile_path)) as archive:
            archive.extractall(self.get_working_dir())

        # fix the permissions so files can be read
        for root, dirs, files in os.walk(self.get_working_dir()):
            for dir_path in dirs:
                os.chmod(os.path.join(root, dir_path),
                         stat.S_IXUSR | stat.S_IWUSR | stat.S_IREAD)
            for file_path in files:
                os.chmod(os.path.join(root, file_path),
                         stat.S_IXUSR | stat.S_IWUSR | stat.S_IREAD)

    def process_main(self, item=None):
        """
        For each layer that we need to save, create the ancestry file
        then call the parent class to finish processing.

        :param item: A docker image unit
        :type item: pulp_docker.plugins.db.models.DockerImage
        """
        # Write out the ancestry file
        ancestry = tarutils.get_ancestry(item.image_id, self.parent.metadata)
        layer_dir = os.path.join(self.get_working_dir(), item.image_id)
        with open(os.path.join(layer_dir, 'ancestry'), 'w') as ancestry_fp:
            json.dump(ancestry, ancestry_fp)

        super(AddDockerUnits, self).process_main(item=item)
