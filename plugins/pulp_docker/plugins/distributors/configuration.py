import os
import re
from urlparse import urlparse

from pulp.server.config import config as server_config
from pulp.server.exceptions import PulpCodedValidationException

from pulp_docker.common import constants, error_codes


def validate_config(config, repo):
    """
    Validate a configuration

    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param repo:   metadata describing the repository to which the
                   configuration applies
    :type  repo:   pulp.server.db.models.Repository
    :raises:       PulpCodedValidationException if any validations failed
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

    # Check that the repo_registry is valid
    repo_registry_id = config.get(constants.CONFIG_KEY_REPO_REGISTRY_ID)
    if repo_registry_id and not _is_valid_repo_registry_id(repo_registry_id):
        errors.append(PulpCodedValidationException(error_code=error_codes.DKR1005,
                                                   field=constants.CONFIG_KEY_REPO_REGISTRY_ID,
                                                   value=repo_registry_id))
    # If the repo_registry_id is not specified, this value defaults to the
    # repo id, so we need to validate that.
    elif not repo_registry_id and not _is_valid_repo_registry_id(repo.repo_id):
        errors.append(PulpCodedValidationException(error_code=error_codes.DKR1006,
                                                   field=constants.CONFIG_KEY_REPO_REGISTRY_ID,
                                                   value=repo.repo_id))

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
    :type  repo: pulp.server.db.models.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or None
    :return: master publishing directory for the given repository
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'master', repo.repo_id)


def get_web_publish_dir(repo, config):
    """
    Get the configured HTTP publication directory.
    Returns the global default if not configured.

    :param repo: repository to get relative path for
    :type  repo: pulp.server.db.models.Repository
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
    :type  repo: pulp.server.db.models.Repository

    :returns: the name to use for the redirect file
    :rtype:  str
    """
    return '%s.json' % repo.repo_id


def get_redirect_url(config, repo):
    """
    Get the redirect URL for a given repo & configuration

    :param config: configuration instance for the repository
    :type  config: pulp.plugins.config.PluginCallConfiguration or dict
    :param repo: repository to get url for
    :type  repo: pulp.server.db.models.Repository

    """
    redirect_url = config.get(constants.CONFIG_KEY_REDIRECT_URL)
    if redirect_url:
        if not redirect_url.endswith('/'):
            redirect_url += '/'
    else:
        # build the redirect URL from the server config
        server_name = server_config.get('server', 'server_name')
        redirect_url = 'https://%s/pulp/docker/%s/' % (server_name, repo.repo_id)

    return redirect_url


def get_repo_relative_path(repo, config):
    """
    Get the configured relative path for the given repository.

    :param repo: repository to get relative path for
    :type  repo: pulp.server.db.models.Repository
    :param config: configuration instance for the repository
    :type  config: pulp.plugins.config.PluginCallConfiguration or dict
    :return: relative path for the repository
    :rtype:  str
    """
    return repo.repo_id


def get_export_repo_directory(config):
    """
    Get the directory where the export publisher will publish repositories.

    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or NoneType
    :return: directory where export files are saved
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config), 'export', 'repo')


def get_export_repo_filename(repo, config):
    """
    Get the file name for a repository export

    :param repo: repository being exported
    :type  repo: pulp.server.db.models.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or NoneType
    :return: The file name for the published tar file
    :rtype:  str
    """
    return '%s.tar' % repo.repo_id


def get_export_repo_file_with_path(repo, config):
    """
    Get the file name to use when exporting a docker repo as a tar file

    :param repo: repository being exported
    :type  repo: pulp.server.db.models.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or NoneType
    :return: The absolute file name for the tar file that will be exported
    :rtype:  str
    """
    file_name = config.get(constants.CONFIG_KEY_EXPORT_FILE)
    if not file_name:
        file_name = os.path.join(get_export_repo_directory(config),
                                 get_export_repo_filename(repo, config))
    return file_name


def get_repo_registry_id(repo, config):
    """
    Get the registry ID that should be used by the docker API.  If a registry name has not
    been specified on the repo fail back to the repo id.

    :param repo: repository to get relative path for
    :type  repo: pulp.server.db.models.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or NoneType
    :return: The name of the repository as it should be represented in in the Docker API
    :rtype:  str
    """
    registry = config.get(constants.CONFIG_KEY_REPO_REGISTRY_ID)
    if not registry:
        registry = repo.repo_id
    return registry


def _is_valid_repo_registry_id(repo_registry_id):
    """
    Docker registry repos are restricted to lower case letters, numbers, hyphens, underscores, and
    periods. Additionally, we allow a single slash for namespacing purposes.

    :param repo_registry_id: Docker registry id
    :type  repo_registry_id: basestring
    :return:                 True if valid, False if invalid
    :rtype:                  boolean
    """
    return bool(re.match(r"^[a-z0-9-_.]*/?[a-z0-9-_.]*$", repo_registry_id))
