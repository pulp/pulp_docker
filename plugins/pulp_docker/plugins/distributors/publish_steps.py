from gettext import gettext as _
import logging
import os
import shutil

from pulp.plugins.util.publish_step import BasePublisher, UnitPublishStep, PublishStep

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import configuration
from pulp_docker.plugins.distributors.metadata import ImagesFileContext, RedirectFileContext

_LOG = logging.getLogger(__name__)


class WebPublisher(BasePublisher):
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
        super(WebPublisher, self).__init__(repo, publish_conduit, config)

        publish_dir = configuration.get_web_publish_dir(repo, config)
        app_file = configuration.get_redirect_file_name(repo)
        app_publish_location = os.path.join(configuration.get_app_publish_dir(config), app_file)
        self.web_working_dir = os.path.join(self.working_dir, 'web')
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.working_dir,
                                                         [('web', publish_dir),
                                                          (app_file, app_publish_location)],
                                                         master_publish_dir,
                                                         step_id=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making files available via web.')
        self.add_process_steps([PublishImagesStep()])
        self.add_post_process_steps([atomic_publish_step])


class PublishImagesStep(UnitPublishStep):
    """
    Publish Images
    """

    def __init__(self):
        super(PublishImagesStep, self).__init__(constants.PUBLISH_STEP_IMAGES,
                                                constants.IMAGE_TYPE_ID)
        self.context = None
        self.redirect_context = None
        self.description = _('Publishing Image Files.')

    def initialize(self):
        """
        Initialize the images file
        """
        self.context = ImagesFileContext(self.get_web_directory(), self.get_conduit())
        self.context.initialize()
        self.redirect_context = RedirectFileContext(self.get_working_dir(),
                                                    self.get_conduit(),
                                                    self.parent.config,
                                                    self.get_repo())
        self.redirect_context.initialize()

    def process_unit(self, unit):
        """
        Link the unit to the image content directory and the package_dir

        :param unit: The unit to process
        :type unit: pulp_docker.common.models.DockerImage
        """
        self.context.add_unit_metadata(unit)
        self.redirect_context.add_unit_metadata(unit)
        target_base = os.path.join(self.get_web_directory(), unit.unit_key['image_id'])
        files = ['ancestry', 'json', 'layer']
        for file_name in files:
            self._create_symlink(os.path.join(unit.storage_path, file_name),
                                 os.path.join(target_base, file_name))

    def finalize(self):
        """
        Close & finalize each the metadata context
        """
        if self.context:
            self.context.finalize()
        if self.redirect_context:
            self.redirect_context.finalize()

    def get_web_directory(self):
        """
        Get the directory where the files published to the web have been linked
        """
        return os.path.join(self.get_working_dir(), 'web')


class AtomicDirectoryPublishStep(PublishStep):
    """
    Perform a publish of a working directory to a published directory with an atomic action.
    This works by first copying the files to a master directory and creating or updating a symbolic
    links in the publish locations

    :param source_dir: The source directory to be copied
    :type source_dir: str
    :param publish_locations: The target locations that are being updated
    :type publish_locations: list of tuples (relative_directory_in_source_dir, publish location)
    :param master_publish_dir: The directory that will contain the master_publish_directories
    :type master_publish_dir: str
    :param step_id: The id of the step, so that this step can be used with custom names.
    :type step_id: str
    """
    def __init__(self, source_dir, publish_locations, master_publish_dir, step_id=None):
        step_id = step_id if step_id else constants.PUBLISH_STEP_DIRECTORY
        super(AtomicDirectoryPublishStep, self).__init__(step_id)
        self.context = None
        self.source_dir = source_dir
        self.publish_locations = publish_locations
        self.master_publish_dir = master_publish_dir

    def process_main(self):
        """
        Publish a directory from the repo to a target directory.
        """

        # Use the timestamp as the name of the current master repository
        # directory. This allows us to identify when these were created as well
        # as having more than one side-by-side during the publishing process.
        timestamp_master_dir = os.path.join(self.master_publish_dir,
                                            self.parent.timestamp)

        # TODO If the timestamp_publish_dir already exists should we assume it is correct?
        # Given that it is timestamped for this publish/repo we could skip the copytree
        # for items where http & https are published to a separate directory

        _LOG.debug('Copying tree from %s to %s' % (self.source_dir, timestamp_master_dir))
        shutil.copytree(self.source_dir, timestamp_master_dir, symlinks=True)

        for source_relative_location, publish_location in self.publish_locations:
            if source_relative_location.startswith('/'):
                source_relative_location = source_relative_location[1::]

            timestamp_master_location = os.path.join(timestamp_master_dir, source_relative_location)
            timestamp_master_location = timestamp_master_location.rstrip('/')

            # Without the trailing '/'
            publish_location = publish_location.rstrip('/')

            # Create the parent directory of the published repository tree, if needed
            publish_dir_parent = os.path.dirname(publish_location)
            if not os.path.exists(publish_dir_parent):
                os.makedirs(publish_dir_parent, 0750)

            # Create a temporary symlink in the parent of the published directory tree
            tmp_link_name = os.path.join(publish_dir_parent, self.parent.timestamp)
            os.symlink(timestamp_master_location, tmp_link_name)

            # Rename the symlink to the official published location name.
            # This has two desirable effects:
            # 1. it will overwrite an existing link, if it's there
            # 2. the operation is atomic, instantly changing the published directory
            # NOTE: it's not easy (possible?) to directly edit the target of a symlink
            os.rename(tmp_link_name, publish_location)

        # Clear out any previously published masters
        self._clear_directory(self.master_publish_dir, skip_list=[self.parent.timestamp])
