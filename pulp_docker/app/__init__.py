from pulpcore.plugin import PulpPluginAppConfig


class PulpDockerPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the docker plugin."""

    name = 'pulp_docker.app'
    label = 'pulp_docker'
