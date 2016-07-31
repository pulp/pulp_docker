import os
import re
from urlparse import urlparse

from pulp.plugins.rsync import configuration as rsync_config
from pulp.server.config import config as server_config
from pulp.server.db.model import Distributor
from pulp.server.exceptions import PulpCodedValidationException

from pulp_docker.common import constants, error_codes


def validate_config(config, repo):
    """
    Validate a configuration

    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param repo:   metadata describing the repository to which the
                   configuration applies
    :type  repo:   pulp.plugins.model.Repository
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
    elif not repo_registry_id and not _is_valid_repo_registry_id(repo.id):
        errors.append(PulpCodedValidationException(error_code=error_codes.DKR1006,
                                                   field=constants.CONFIG_KEY_REPO_REGISTRY_ID,
                                                   value=repo.id))

    if errors:
        raise PulpCodedValidationException(validation_exceptions=errors)

    return True, None


def validate_rsync_distributor_config(repo, config, config_conduit):
    """
    Performs validation of configuration that is standard for all rsync distributors. Then performs
    extra validation needed for docker rsync.

    :param repo:   metadata describing the repository to which the
                   configuration applies
    :type  repo:   pulp.plugins.model.Repository
    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param config_conduit: Configuration Conduit;
    :type  config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit

    :return: tuple comprised of a boolean indicating whether validation succeeded or failed and a
             list of errors (if any)
    :rtype: (bool, list of strings) or (bool, None)
    :raises: PulpCodedValidationException if any validations failed
    """
    valid, errors = rsync_config.validate_config(repo, config, config_conduit)
    if valid:
        return validate_postdistributor(repo, config)
    else:
        return valid, errors


def validate_postdistributor(repo, config):
    """
    Validates that the postdistributor_id is set and is valid for this repositotry.

    :param repo:   metadata describing the repository to which the configuration applies
    :type  repo:   pulp.plugins.model.Repository
    :param config: Pulp configuration for the distributor
    :type  config: pulp.plugins.config.PluginCallConfiguration

    :return: tuple comprised of a boolean indicating whether validation succeeded or failed and a
             list of errors (if any)
    :rtype: (bool, list of strings) or (bool, None)
    :raises: PulpCodedValidationException if postdistributor_id is not defined or 404 if the
             distributor_id is not associated with the repo

    """
    postdistributor = config.flatten().get("postdistributor_id", None)
    if postdistributor:
        Distributor.objects.get_or_404(repo_id=repo.id, distributor_id=postdistributor)
        return True, None
    else:
        raise PulpCodedValidationException(error_code=error_codes.DKR1009)


def get_root_publish_directory(config, docker_api_version):
    """
    The publish directory for the docker plugin

    :param config:             Pulp configuration for the distributor
    :type  config:             pulp.plugins.config.PluginCallConfiguration
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring
    :return:                   The publish directory for the docker plugin
    :rtype:                    str
    """
    return os.path.join(config.get(constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY),
                        docker_api_version)


def get_master_publish_dir(repo, config, docker_api_version):
    """
    Get the master publishing directory for the given repository.
    This is the directory that links/files are actually published to
    and linked from the directory published by the web server in an atomic action.

    :param repo:               repository to get the master publishing directory for
    :type  repo:               pulp.plugins.model.Repository
    :param config:             configuration instance
    :type  config:             pulp.plugins.config.PluginCallConfiguration or None
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring
    :return:                   master publishing directory for the given repository
    :rtype:                    str
    """
    return os.path.join(get_root_publish_directory(config, docker_api_version), 'master', repo.id)


def get_web_publish_dir(repo, config, docker_api_version):
    """
    Get the configured HTTP publication directory.
    Returns the global default if not configured.

    :param repo:               repository to get relative path for
    :type  repo:               pulp.plugins.model.Repository
    :param config:             configuration instance
    :type  config:             pulp.plugins.config.PluginCallConfiguration or None
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring

    :return: the HTTP publication directory
    :rtype:  str
    """
    return os.path.join(get_root_publish_directory(config, docker_api_version), 'web',
                        get_repo_relative_path(repo, config))


def get_app_publish_dir(config, docker_api_version):
    """
    Get the configured directory where the application redirect files should be stored

    :param config:             configuration instance
    :type  config:             pulp.plugins.config.PluginCallConfiguration or None
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring

    :returns:                  the name to use for the redirect file
    :rtype:                    str
    """
    return os.path.join(get_root_publish_directory(config, docker_api_version), 'app',)


def get_redirect_file_name(repo):
    """
    Get the name to use when generating the redirect file for a repository

    :param repo: the repository to get the app file name for
    :type  repo: pulp.plugins.model.Repository

    :returns: the name to use for the redirect file
    :rtype:  str
    """
    return '%s.json' % repo.id


def get_redirect_url(config, repo, docker_api_version):
    """
    Get the redirect URL for a given repo & configuration

    :param config:             configuration instance for the repository
    :type  config:             pulp.plugins.config.PluginCallConfiguration or dict
    :param repo:               repository to get url for
    :type  repo:               pulp.plugins.model.Repository
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring
    :return:                   The redirect URL for the given config, repo, and Docker version
    :rtype:                    basestring
    """
    redirect_url = config.get(constants.CONFIG_KEY_REDIRECT_URL)
    if redirect_url:
        if not redirect_url.endswith('/'):
            redirect_url += '/'
    else:
        # build the redirect URL from the server config
        server_name = server_config.get('server', 'server_name')
        redirect_url = 'https://%s/pulp/docker/%s/%s/' % (server_name, docker_api_version, repo.id)

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


def get_export_repo_directory(config, docker_api_version):
    """
    Get the directory where the export publisher will publish repositories.

    :param config:             configuration instance
    :type  config:             pulp.plugins.config.PluginCallConfiguration or NoneType
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring
    :return:                   directory where export files are saved
    :rtype:                    str
    """
    return os.path.join(get_root_publish_directory(config, docker_api_version), 'export', 'repo')


def get_export_repo_filename(repo, config):
    """
    Get the file name for a repository export

    :param repo: repository being exported
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or NoneType
    :return: The file name for the published tar file
    :rtype:  str
    """
    return '%s.tar' % repo.id


def get_export_repo_file_with_path(repo, config, docker_api_version):
    """
    Get the file name to use when exporting a docker repo as a tar file

    :param repo:               repository being exported
    :type  repo:               pulp.plugins.model.Repository
    :param config:             configuration instance
    :type  config:             pulp.plugins.config.PluginCallConfiguration or NoneType
    :param docker_api_version: The Docker API version that is being published ('v1' or 'v2')
    :type  docker_api_version: basestring
    :return:                   The absolute file name for the tar file that will be exported
    :rtype:                    str
    """
    file_name = config.get(constants.CONFIG_KEY_EXPORT_FILE)
    if not file_name:
        file_name = os.path.join(get_export_repo_directory(config, docker_api_version),
                                 get_export_repo_filename(repo, config))
    return file_name


def get_repo_registry_id(repo, config):
    """
    Get the registry ID that should be used by the docker API.  If a registry name has not
    been specified on the repo fail back to the repo id.

    :param repo: repository to get relative path for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance
    :type  config: pulp.plugins.config.PluginCallConfiguration or NoneType
    :return: The name of the repository as it should be represented in in the Docker API
    :rtype:  str
    """
    registry = config.get(constants.CONFIG_KEY_REPO_REGISTRY_ID)
    if not registry:
        registry = repo.id
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
