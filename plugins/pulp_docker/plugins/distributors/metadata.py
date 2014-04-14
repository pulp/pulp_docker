import logging
import os

from pulp.server.compat import json
from pulp.plugins.util.metadata_writer import JSONArrayFileContext


_LOG = logging.getLogger(__name__)

IMAGES_FILE_NAME = 'images.json'


class ImagesFileContext(JSONArrayFileContext):
    """
    Context manager for generating the docker images file.
    """

    def __init__(self, working_dir, repo):
        """
        :param working_dir: working directory to create the filelists.xml.gz in
        :type  working_dir: str
        :param repo: The repo that contains all the image tag information
        :type repo: pulp.plugins.model.Repository
        """
        metadata_file_path = os.path.join(working_dir, IMAGES_FILE_NAME)
        super(ImagesFileContext, self).__init__(metadata_file_path)
        self.repo = repo

    def add_unit_metadata(self, unit):
        """
        Add the specific metadata for this unit

        :param unit: The docker unit to add to the images metadata file
        :type unit: pulp_docker.common.models.DockerImage
        """
        super(ImagesFileContext, self).add_unit_metadata(unit)
        # TODO Add the tags
        unit_data = {
            'id': unit.image_id
        }
        string_representation = json.dumps(unit_data)
        self.metadata_file_handle.write(string_representation)
