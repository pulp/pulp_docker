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

    def __init__(self, working_dir, conduit):
        """
        :param working_dir: working directory to create the filelists.xml.gz in
        :type  working_dir: str
        :param conduit: The conduit to get api calls
        :type conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        """
        metadata_file_path = os.path.join(working_dir, IMAGES_FILE_NAME)
        super(ImagesFileContext, self).__init__(metadata_file_path)
        scratchpad = conduit.get_repo_scratchpad()
        tags = scratchpad[u'tags']
        self.labels = {}
        for tag_name, image_name in tags.iteritems():
            self.labels[image_name] = tag_name

    def add_unit_metadata(self, unit):
        """
        Add the specific metadata for this unit

        :param unit: The docker unit to add to the images metadata file
        :type unit: pulp.plugins.model.AssociatedUnit
        """
        super(ImagesFileContext, self).add_unit_metadata(unit)
        image_id = unit.unit_key['image_id']
        unit_data = {
            'id': image_id
        }
        if self.labels.get(image_id):
            unit_data.update({'Tag': self.labels.get(image_id)})

        string_representation = json.dumps(unit_data)
        self.metadata_file_handle.write(string_representation)
