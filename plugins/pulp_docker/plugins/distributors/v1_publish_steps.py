from gettext import gettext as _
import os

from pulp.plugins.util import misc
from pulp.plugins.util.publish_step import PublishStep, UnitModelPluginStep, \
    AtomicDirectoryPublishStep, SaveTarFilePublishStep

from pulp_docker.common import constants
from pulp_docker.plugins import models
from pulp_docker.plugins.distributors import configuration
from pulp_docker.plugins.distributors.metadata import RedirectFileContext


class WebPublisher(PublishStep):
    """
    Docker Web publisher class that is responsible for the actual publishing
    of a docker repository via a web server
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(WebPublisher, self).__init__(
            step_type=constants.PUBLISH_STEP_WEB_PUBLISHER, repo=repo,
            publish_conduit=publish_conduit, config=config)

        docker_api_version = 'v1'
        publish_dir = configuration.get_web_publish_dir(repo, config, docker_api_version)
        app_file = configuration.get_redirect_file_name(repo)
        app_publish_location = os.path.join(
            configuration.get_app_publish_dir(config, docker_api_version), app_file)
        self.working_dir = os.path.join(self.get_working_dir(), docker_api_version)
        misc.mkdir(self.working_dir)
        self.web_working_dir = os.path.join(self.get_working_dir(), 'web')
        master_publish_dir = configuration.get_master_publish_dir(repo, config, docker_api_version)
        atomic_publish_step = AtomicDirectoryPublishStep(self.get_working_dir(),
                                                         [('web', publish_dir),
                                                          (app_file, app_publish_location)],
                                                         master_publish_dir,
                                                         step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making v1 files available via web.')
        self.add_child(PublishImagesStep())
        self.add_child(atomic_publish_step)


class ExportPublisher(PublishStep):
    """
    Docker Export publisher class that is responsible for the actual publishing
    of a docker repository via a tar file
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(ExportPublisher, self).__init__(
            step_type=constants.PUBLISH_STEP_EXPORT_PUBLISHER, repo=repo,
            publish_conduit=publish_conduit, config=config)

        self.add_child(PublishImagesStep())
        tar_file = configuration.get_export_repo_file_with_path(repo, config, 'v1')
        self.add_child(SaveTarFilePublishStep(self.get_working_dir(), tar_file))


class PublishImagesStep(UnitModelPluginStep):
    """
    Publish Images
    """

    def __init__(self):
        super(PublishImagesStep, self).__init__(step_type=constants.PUBLISH_STEP_IMAGES,
                                                model_classes=[models.Image])
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Image Files.')

    def initialize(self):
        """
        Initialize the metadata contexts
        """
        self.redirect_context = RedirectFileContext(self.parent.get_working_dir(),
                                                    self.get_conduit(),
                                                    self.parent.config,
                                                    self.get_repo())
        self.redirect_context.initialize()

    def process_unit(self, unit):
        """
        Link the unit to the image content directory and the package_dir

        :param unit: The unit to process
        :type unit:  pulp_docker.common.models.Image
        """
        self.redirect_context.add_unit_metadata(unit)
        target_base = os.path.join(self.get_web_directory(), unit.unit_key['image_id'])
        files = ['ancestry', 'json', 'layer']
        for file_name in files:
            misc.create_symlink(os.path.join(unit.storage_path, file_name),
                                os.path.join(target_base, file_name))

    def finalize(self):
        """
        Close & finalize each the metadata context
        """
        if self.redirect_context:
            self.redirect_context.finalize()

    def get_web_directory(self):
        """
        Get the directory where the files published to the web have been linked
        """
        return os.path.join(self.parent.get_working_dir(), 'web')
