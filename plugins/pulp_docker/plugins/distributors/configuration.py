import os
import logging
from urlparse import urlparse

from pulp.server.exceptions import PulpCodedValidationException

from pulp_docker.common import constants, error_codes

_LOG = logging.getLogger(__name__)


def validate_config(config):
    """
    Validate a configuration

    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :raises: PulpCodedValidationException if any validations failed
    """
    errors = []
    server_url = config.get(constants.CONFIG_KEY_SERVER_URL)
    if server_url:
        parsed = urlparse(server_url)
        if not parsed.scheme:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1001,
                                                       field=constants.CONFIG_KEY_SERVER_URL,
                                                       url=server_url))
        if not parsed.netloc:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1002,
                                                       field=constants.CONFIG_KEY_SERVER_URL,
                                                       url=server_url))
        if not parsed.path:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1003,
                                                       field=constants.CONFIG_KEY_SERVER_URL,
                                                       url=server_url))
    protected = config.get(constants.CONFIG_KEY_PROTECTED)
    if protected:
        protected_parsed = config.get_boolean(constants.CONFIG_KEY_PROTECTED)
        if protected_parsed is None:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1004,
                                                       field=constants.CONFIG_KEY_PROTECTED,
                                                       value=protected))

    if errors:
        raise PulpCodedValidationException(validation_exceptions=errors)

    return True, None


def get_root_publish_directory(config):
    """
    The publish directory for the docker plugin

    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :return: The publish directory for the docker plugin
    :rtype: str
    """
    return config.get(constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY)


def get_master_publish_dir(repo, config):
    """
    Get the master publishing directory for the given repository.
    This is the directory that links/files are actually published to
    and linked from the directory published by the web server in an atomic action.

    :param repo: repository to get the master publishing directory for
    :type  repo: pulp.plugins.model.Repository
    :return: master publishing directory for the given repository
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'master', repo.id)


def get_web_publish_dir(repo, config):
    """
    Get the configured HTTP publication directory.
    Returns the global default if not configured.

    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None

    :return: the HTTP publication directory
    :rtype:  str
    """

    return os.path.join(get_root_publish_directory(config),
                        'web',
                        get_repo_relative_path(repo, config))


def get_repo_relative_path(repo, config):
    """
    Get the configured relative path for the given repository.

    :param repo: repository to get relative path for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance for the repository
    :type  config: pulp.plugins.config.PluginCallConfiguration or dict
    :return: relative path for the repository
    :rtype:  str
    """
    return repo.id
