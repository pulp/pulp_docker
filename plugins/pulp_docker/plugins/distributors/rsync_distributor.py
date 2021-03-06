from gettext import gettext as _
import logging

from pulp.common.config import read_json_config
from pulp.plugins.distributor import Distributor

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import configuration
from pulp_docker.plugins.distributors.publish_steps import DockerRsyncPublisher

TYPE_ID_DISTRIBUTOR_DOCKER_RSYNC = 'docker_rsync_distributor'
CONF_FILE_PATH = 'server/plugins.conf.d/%s.json' % TYPE_ID_DISTRIBUTOR_DOCKER_RSYNC

DISTRIBUTOR_DISPLAY_NAME = 'Docker Rsync Distributor'


_LOG = logging.getLogger(__name__)


# -- entry point ---------------------------------------------------------------

def entry_point():
    config = read_json_config(CONF_FILE_PATH)
    return DockerRsyncDistributor, config


class DockerRsyncDistributor(Distributor):
    """
    Distributor class for publishing repo directory to RH CDN
    """

    def __init__(self):
        super(DockerRsyncDistributor, self).__init__()

        self.canceled = False
        self._publisher = None

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this distributor.

        :return: description of the distributor's capabilities
        :rtype:  dict
        """
        return {'id': TYPE_ID_DISTRIBUTOR_DOCKER_RSYNC,
                'display_name': DISTRIBUTOR_DISPLAY_NAME,
                'types': constants.SUPPORTED_TYPES}

    # -- repo lifecycle methods ------------------------------------------------

    def validate_config(self, repo, config, config_conduit):
        """
        Allows the distributor to check the contents of a potential configuration
        for the given repository. This call is made both for the addition of
        this distributor to a new repository as well as updating the configuration
        for this distributor on a previously configured repository.

        :param repo: metadata describing the repository to which the
                     configuration applies
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration instance; the proposed repo
                       configuration is found within
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :param config_conduit: Configuration Conduit;
        :type  config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit

        :return: tuple of (bool, str) to describe the result
        :rtype:  tuple
        """
        _LOG.debug(_('Validating docker repository configuration: %(repoid)s') %
                   {'repoid': repo.id})
        return configuration.validate_rsync_distributor_config(repo, config, config_conduit)

    # -- actions ---------------------------------------------------------------

    def publish_repo(self, repo, publish_conduit, config):
        """
        Publishes the given repository.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param publish_conduit: provides access to relevant Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginConfiguration

        :return: report describing the publish run
        :rtype:  pulp.plugins.model.PublishReport
        """
        _LOG.debug(_('Publishing Docker repository: %(repoid)s') % {'repoid': repo.id})
        self._publisher = DockerRsyncPublisher(repo, publish_conduit, config,
                                               TYPE_ID_DISTRIBUTOR_DOCKER_RSYNC)
        return self._publisher.publish()
