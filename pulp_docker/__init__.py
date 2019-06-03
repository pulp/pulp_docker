import pkg_resources

__version__ = pkg_resources.get_distribution("pulp-docker").version


default_app_config = 'pulp_docker.app.PulpDockerPluginAppConfig'
