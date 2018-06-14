from pulpcore.plugin import PulpPluginAppConfig


class PulpDockerPluginAppConfig(PulpPluginAppConfig):
    name = 'pulp_docker.app'
    label = 'pulp_docker'
