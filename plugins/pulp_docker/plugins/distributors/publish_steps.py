from gettext import gettext as _
import logging
import os

from mongoengine import Q
from pulp.plugins.util.publish_step import PluginStep, \
    AtomicDirectoryPublishStep, SaveTarFilePublishStep
from pulp.plugins.util import misc as plugin_utils
from pulp.server.controllers import repository as repo_controller

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import configuration
from pulp_docker.plugins.distributors.metadata import RedirectFileContext


_LOG = logging.getLogger(__name__)


class WebPublisher(PluginStep):
    """
    Docker Web publisher class that is responsible for the actual publishing
    of a docker repository via a web server
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo: Pulp managed Yum repository.
        :type  repo: pulp.server.db.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(WebPublisher, self).__init__(constants.PUBLISH_STEP_WEB_PUBLISHER,
                                           repo, publish_conduit, config)

        publish_dir = configuration.get_web_publish_dir(repo, config)
        app_file = configuration.get_redirect_file_name(repo)
        app_publish_location = os.path.join(configuration.get_app_publish_dir(config), app_file)
        self.web_working_dir = os.path.join(self.get_working_dir(), 'web')
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.get_working_dir(),
                                                         [('web', publish_dir),
                                                          (app_file, app_publish_location)],
                                                         master_publish_dir,
                                                         step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making files available via web.')
        self.add_child(PublishImagesStep())
        self.add_child(atomic_publish_step)


class ExportPublisher(PluginStep):
    """
    Docker Export publisher class that is responsible for the actual publishing
    of a docker repository via a tar file
    """

    def __init__(self, repo, publish_conduit, config):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.server.db.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(ExportPublisher, self).__init__(constants.PUBLISH_STEP_EXPORT_PUBLISHER,
                                              repo, publish_conduit, config)

        self.add_child(PublishImagesStep())
        tar_file = configuration.get_export_repo_file_with_path(repo, config)
        self.add_child(SaveTarFilePublishStep(self.get_working_dir(), tar_file))


class PublishImagesStep(PluginStep):
    """
    Publish Images
    """

    def __init__(self):
        super(PublishImagesStep, self).__init__(constants.PUBLISH_STEP_IMAGES)

        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Image Files.')

    def initialize(self):
        """
        Initialize the metadata contexts
        """
        self.redirect_context = RedirectFileContext(self.get_working_dir(),
                                                    self.get_conduit(),
                                                    self.parent.config,
                                                    self.get_repo())
        self.redirect_context.initialize()

    def get_total(self):
        """
        Get the total number of images to publish.

        The value returned should not change during the processing of the step.

        :returns: The total number of images to publish
        :rtype: int
        """
        repo = self.get_repo()
        return repo.content_unit_counts.get(constants.IMAGE_TYPE_ID, 0)

    def get_iterator(self):
        """
        This method returns a generator to loop over items.
        The items created by this generator will be iterated over by the process_main method.

        :return: a list or other iterable
        :rtype: iterator of pulp_docker.plugins.db.models.DockerImage
        """

        return repo_controller.find_repo_content_units(
            self.get_repo(),
            repo_content_unit_q=Q(unit_type_id=constants.IMAGE_TYPE_ID),
            yield_content_unit=True)

    def process_main(self, item=None):

        """
        Link the unit to the image content directory and the package_dir

        :param item: The unit to process
        :type item: pulp_docker.plugins.db.models.DockerImage
        """
        self.redirect_context.add_unit_metadata(item)
        target_base = os.path.join(self.get_web_directory(), item.image_id)
        files = ['ancestry', 'json', 'layer']
        for file_name in files:
            plugin_utils.create_symlink(os.path.join(item.storage_path, file_name),
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
        return os.path.join(self.get_working_dir(), 'web')
