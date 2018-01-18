from gettext import gettext as _
import copy
import logging
import os
import shutil

from pulp.common.config import read_json_config
from pulp.plugins.distributor import Distributor

from pulp_docker.common import constants
from pulp_docker.plugins.distributors.publish_steps import WebPublisher
from pulp_docker.plugins.distributors import configuration


_logger = logging.getLogger(__name__)

PLUGIN_DEFAULT_CONFIG = {
    constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: constants.CONFIG_VALUE_DOCKER_PUBLISH_DIRECTORY
}


def entry_point():
    """
    Entry point that pulp platform uses to load the distributor
    :return: distributor class and its config
    :rtype:  Distributor, dict
    """
    plugin_config = copy.deepcopy(PLUGIN_DEFAULT_CONFIG)
    edited_config = read_json_config(constants.DISTRIBUTOR_CONFIG_FILE_NAME)

    plugin_config.update(edited_config)
    return DockerWebDistributor, plugin_config


class DockerWebDistributor(Distributor):
    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this distributor. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this distributor. Must be unique
          across all distributors. Only letters and underscores are valid.
        * display_name - User-friendly identification of the distributor.
        * types - List of all content type IDs that may be published using this
          distributor.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': constants.DISTRIBUTOR_WEB_TYPE_ID,
            'display_name': _('Docker Web Distributor'),
            'types': constants.SUPPORTED_TYPES,
        }

    def __init__(self):
        super(DockerWebDistributor, self).__init__()
        self._publisher = None
        self.canceled = False

    def validate_config(self, repo, config, config_conduit):
        """
        Allows the distributor to check the contents of a potential configuration
        for the given repository. This call is made both for the addition of
        this distributor to a new repository as well as updating the configuration
        for this distributor on a previously configured repository. The implementation
        should use the given repository data to ensure that updating the
        configuration does not put the repository into an inconsistent state.

        The return is a tuple of the result of the validation (True for success,
        False for failure) and a message. The message may be None and is unused
        in the success case. For a failed validation, the message will be
        communicated to the caller so the plugin should take i18n into
        consideration when generating the message.

        The related_repos parameter contains a list of other repositories that
        have a configured distributor of this type. The distributor configurations
        is found in each repository in the "plugin_configs" field.

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
        return configuration.validate_config(config, repo)

    def publish_repo(self, repo, publish_conduit, config):
        """
        Publishes the given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the publish is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the distributor to rollback any changes
        that have been made.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param publish_conduit: provides access to relevant Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginConfiguration

        :return: report describing the publish run
        :rtype:  pulp.plugins.model.PublishReport
        """
        _logger.debug('Publishing docker repository: %s' % repo.id)
        self._publisher = WebPublisher(repo, publish_conduit, config)
        return self._publisher.publish()

    def cancel_publish_repo(self):
        """
        Call cancellation control hook.
        """
        _logger.debug('Canceling docker repository publish')
        self.canceled = True
        if self._publisher is not None:
            self._publisher.cancel()

    def distributor_removed(self, repo, config):
        """
        Called when a distributor of this type is removed from a repository.
        This hook allows the distributor to clean up any files that may have
        been created during the actual publishing.

        The distributor may use the contents of the working directory in cleanup.
        It is not required that the contents of this directory be deleted by
        the distributor; Pulp will ensure it is wiped following this call.

        If this call raises an exception, the distributor will still be removed
        from the repository and the working directory contents will still be
        wiped by Pulp.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        # remove the directories that might have been created for this repo/distributor
        dir_list = [repo.working_dir,
                    configuration.get_master_publish_dir(repo, config, "v1"),
                    configuration.get_master_publish_dir(repo, config, "v2"),
                    configuration.get_web_publish_dir(repo, config, "v1"),
                    configuration.get_web_publish_dir(repo, config, "v2")]

        for repo_dir in dir_list:
            # in case repo_dir is None
            # ingore_errors set to True does not cover this.
            if repo_dir:
                shutil.rmtree(repo_dir, ignore_errors=True)

        # Remove the published app file & directory links
        dir_list = [configuration.get_web_publish_dir(repo, config, "v1"),
                    configuration.get_web_publish_dir(repo, config, "v2"),
                    os.path.join(configuration.get_app_publish_dir(config, "v1"),
                                 configuration.get_redirect_file_name(repo)),
                    os.path.join(configuration.get_app_publish_dir(config, "v2"),
                                 configuration.get_redirect_file_name(repo))]

        for repo_dir in dir_list:
            try:
                os.unlink(repo_dir)
            except OSError:
                # It's fine if this file doesn't exist
                pass
