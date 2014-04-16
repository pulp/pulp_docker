import logging
import os


from pulp.server.compat import json
from pulp.plugins.util.metadata_writer import JSONArrayFileContext

from pulp_docker.plugins.distributors import configuration

_LOG = logging.getLogger(__name__)

IMAGES_FILE_NAME = 'images.json'


def build_tag_dict(conduit):
    """
    Build the mapping for image id to tags

    :param conduit: The conduit to get api calls
    :type conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
    """
    scratchpad = conduit.get_repo_scratchpad()
    tags = scratchpad[u'tags']
    labels = {}
    for tag_name, image_name in tags.iteritems():
        tag_list = labels.get(image_name)
        if not tag_list:
            tag_list = []
            labels[image_name] = tag_list
        tag_list.append(tag_name)
    return labels


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

        string_representation = json.dumps(unit_data)
        self.metadata_file_handle.write(string_representation)


class RedirectFileContext(JSONArrayFileContext):
    """
    Context manager for generating the docker images file.
    """

    def __init__(self, working_dir, conduit, config, repo):
        """
        :param working_dir: working directory to create the filelists.xml.gz in
        :type  working_dir: str
        :param conduit: The conduit to get api calls
        :type conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        :param repo: Pulp managed repository
        :type  repo: pulp.plugins.model.Repository
        """

        self.repo_id = repo.id
        metadata_file_path = os.path.join(working_dir,
                                          configuration.get_redirect_file_name(repo))
        super(RedirectFileContext, self).__init__(metadata_file_path)
        self.labels = build_tag_dict(conduit)
        self.redirect_url = configuration.get_redirect_url(config, repo)

    def _write_file_header(self):
        """
        Write out the beginning of the json file
        """

        self.metadata_file_handle.write('{"type":"pulp-docker-redirect","version":1,'
                                        '"repository":"%s","data":[' % self.repo_id)

    def _write_file_footer(self):
        """
        Write out the end of the json file
        """
        self.metadata_file_handle.write(']}')

    def add_unit_metadata(self, unit):
        """
        Add the specific metadata for this unit

        :param unit: The docker unit to add to the images metadata file
        :type unit: pulp.plugins.model.AssociatedUnit
        """
        super(RedirectFileContext, self).add_unit_metadata(unit)
        image_id = unit.unit_key['image_id']
        unit_data = {
            'id': image_id,
            'url': self.redirect_url + image_id + '/'
        }
        if self.labels.get(image_id):
            unit_data.update({'tags': self.labels.get(image_id)})

        string_representation = json.dumps(unit_data)
        self.metadata_file_handle.write(string_representation)
