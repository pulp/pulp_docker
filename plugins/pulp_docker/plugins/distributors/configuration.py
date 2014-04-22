import logging
import os
from urlparse import urlparse

from pulp.server.config import config as server_config
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
    server_url = config.get(constants.CONFIG_KEY_REDIRECT_URL)
    if server_url:
        parsed = urlparse(server_url)
        if not parsed.scheme:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1001,
                                                       field=constants.CONFIG_KEY_REDIRECT_URL,
                                                       url=server_url))
        if not parsed.netloc:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1002,
                                                       field=constants.CONFIG_KEY_REDIRECT_URL,
                                                       url=server_url))
        if not parsed.path:
            errors.append(PulpCodedValidationException(error_code=error_codes.DKR1003,
                                                       field=constants.CONFIG_KEY_REDIRECT_URL,
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
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: master publishing directory for the given repository
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'master', repo.id)


def get_web_publish_dir(repo, config):
    """
    Get the configured HTTP publication directory.
    Returns the global default if not configured.

    :param repo: repository to get relative path for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None

    :return: the HTTP publication directory
    :rtype:  str
    """

    return os.path.join(get_root_publish_directory(config),
                        'web',
                        get_repo_relative_path(repo, config))


def get_app_publish_dir(config):
    """
    Get the configured directory where the application redirect files should be stored

    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None

    :returns: the name to use for the redirect file
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'app',)


def get_redirect_file_name(repo):
    """
    Get the name to use when generating the redirect file for a repository

    :param repo: the repository to get the app file name for
    :type  repo: pulp.plugins.model.Repository

    :returns: the name to use for the redirect file
    :rtype:  str
    """
    return '%s.json' % repo.id


def get_redirect_url(config, repo):
    """
    Get the redirect URL for a given repo & configuration

    :param config: configuration instance for the repository
    :type  config: pulp.plugins.config.PluginCallConfiguration or dict
    :param repo: repository to get url for
    :type  repo: pulp.plugins.model.Repository

    """
    redirect_url = config.get(constants.CONFIG_KEY_REDIRECT_URL)
    if redirect_url:
        if not redirect_url.endswith('/'):
            redirect_url += '/'
    else:
        # build the redirect URL from the server config
        server_name = server_config.get('server', 'server_name')
        redirect_url = 'https://%s/pulp/docker/%s/' % (server_name, repo.id)

    return redirect_url


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


def get_export_repo_directory(config):
    """
    Get the directory where the export publisher will publish repositories.

    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: directory where export files are saved
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'export', 'repo')


def get_export_repo_filename(repo, config):
    """

    Get the file name for a repository export

    :param repo: repository to get relative path for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: The file name for the published tar file
    :rtype:  str
    """
    return '%s.tar' % repo.id
