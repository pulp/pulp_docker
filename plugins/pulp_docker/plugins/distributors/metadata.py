import logging
import os


from pulp.server.compat import json
from pulp.plugins.util.metadata_writer import JSONArrayFileContext

from pulp_docker.plugins.distributors import configuration

_LOG = logging.getLogger(__name__)


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
        scratchpad = conduit.get_repo_scratchpad()
        self.tags = scratchpad.get(u'tags', {})
        self.registry = configuration.get_repo_registry_id(repo, config)

        self.redirect_url = configuration.get_redirect_url(config, repo)

    def _write_file_header(self):
        """
        Write out the beginning of the json file
        """
        self.metadata_file_handle.write('{"type":"pulp-docker-redirect","version":1,'
                                        '"repository":"%s","repo-registry-id": "%s",'
                                        '"url":"%s","images":[' %
                                        (self.repo_id, self.registry, self.redirect_url))

    def _write_file_footer(self):
        """
        Write out the end of the json file
        """
        self.metadata_file_handle.write('],"tags":')
        self.metadata_file_handle.write(json.dumps(self.tags))
        self.metadata_file_handle.write('}')

    def add_unit_metadata(self, unit):
        """
        Add the specific metadata for this unit

        :param unit: The docker unit to add to the images metadata file
        :type unit: pulp.plugins.model.AssociatedUnit
        """
        super(RedirectFileContext, self).add_unit_metadata(unit)
        image_id = unit.unit_key['image_id']
        unit_data = {
            'id': image_id
        }
        string_representation = json.dumps(unit_data)
        self.metadata_file_handle.write(string_representation)
