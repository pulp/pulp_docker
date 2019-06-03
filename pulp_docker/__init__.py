import pkg_resources

__version__ = pkg_resources.get_distribution("pulp_docker").version


default_app_config = 'pulp_docker.app.PulpDockerPluginAppConfig'
