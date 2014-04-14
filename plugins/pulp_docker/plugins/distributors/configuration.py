import os
import logging

from pulp.common import error_codes
from pulp.server.exceptions import PulpCodedValidationException
from pulp_docker.common import constants


_LOG = logging.getLogger(__name__)


def validate_config(config):
    """
    Validate a configuration

    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :raises: PulpCodedValidationException if any validations failed
    """
    errors = []
    relative_url = config.get(constants.CONFIG_KEY_RELATIVE_URL)
    if relative_url:
        # Make sure the relative url doesn't start with a path separator
        if relative_url.startswith(os.path.sep):
            errors.append(PulpCodedValidationException(error_code=error_codes.PLP1006,
                                                       field=constants.CONFIG_KEY_RELATIVE_URL,
                                                       value=relative_url))
        else:
            # Make sure a relative url is sandboxed to the parent directory.
            prefix = '/tmp/foo/bar'
            result = os.path.normpath(os.path.join(prefix, relative_url))
            if not result.startswith(prefix):
                errors.append(PulpCodedValidationException(error_code=error_codes.PLP1007,
                                                           path=relative_url))
            else:
                # Validate a second path to ensure that this still breaks if they relative
                # path override went to /tmp/foo/bar
                prefix = '/baz/flux'
                result = os.path.normpath(os.path.join(prefix, relative_url))
                if not result.startswith(prefix):
                    errors.append(PulpCodedValidationException(error_code=error_codes.PLP1007,
                                                               path=relative_url))

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
    relative_path = config.get(constants.CONFIG_KEY_RELATIVE_URL, repo.id) or repo.id

    if relative_path.startswith('/'):
        relative_path = relative_path[1:]

    return relative_path
