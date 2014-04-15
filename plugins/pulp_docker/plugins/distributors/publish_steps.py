from gettext import gettext as _
import logging
import os
import shutil

from pulp.plugins.util.publish_step import BasePublisher, UnitPublishStep, PublishStep

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import configuration
from pulp_docker.plugins.distributors.metadata import ImagesFileContext

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
        master_publish_dir = configuration.get_master_publish_dir(repo, config)
        atomic_publish_step = AtomicDirectoryPublishStep(self.working_dir,
                                                         publish_dir,
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
        self.description = _('Publishing Image Files.')

    def initialize(self):
        """
        Initialize the images file
        """
        self.context = ImagesFileContext(self.get_working_dir(), self.get_conduit())
        self.context.initialize()

    def process_unit(self, unit):
        """
        Link the unit to the image content directory and the package_dir

        :param unit: The unit to process
        :type unit: pulp_docker.common.models.DockerImage
        """
        self.context.add_unit_metadata(unit)
        target_base = os.path.join(self.get_working_dir(), unit.unit_key['image_id'])
        files = ['ancestry', 'json', 'layer']
        for file_name in files:
            self._create_symlink(os.path.join(unit.storage_path, file_name),
                                 os.path.join(target_base, file_name))

    def finalize(self):
        """
        Close & finalize each the metadata context
        """
        self.context.finalize()


class AtomicDirectoryPublishStep(PublishStep):
    """
    Perform a publish of a working directory to a published directory with an atomic action.
    This works by first copying the files to a master directory and creating or updating a symbolic
    link in the target location.

    :param source_dir: The source directory to be copied
    :type source_dir: str
    :param publish_dir: The directory target directory that is being updated
    :type publish_dir: str
    :param master_publish_dir: The directory that will contain the master_publish_directories
    :type master_publish_dir: str
    :param step_id: The id of the step, so that this step can be used with custom names.
    :type step_id: str
    """
    def __init__(self, source_dir, publish_dir, master_publish_dir, step_id=None):
        step_id = step_id if step_id else constants.PUBLISH_STEP_DIRECTORY
        super(AtomicDirectoryPublishStep, self).__init__(step_id)
        self.context = None
        self.source_dir = source_dir
        self.publish_dir = publish_dir
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

        # Without the trailing '/'
        if self.publish_dir.endswith('/'):
            self.publish_dir = self.publish_dir[:-1]

        # Create the parent directory of the published repository tree, if needed
        publish_dir_parent = self.publish_dir.rsplit('/', 1)[0]
        if not os.path.exists(publish_dir_parent):
            os.makedirs(publish_dir_parent, 0750)

        # Create a temporary symlink in the parent of the published directory tree
        tmp_link_name = os.path.join(publish_dir_parent, self.parent.timestamp)
        os.symlink(timestamp_master_dir, tmp_link_name)

        # Rename the symlink to the official published repository directory name.
        # This has two desirable effects:
        # 1. it will overwrite an existing link, if it's there
        # 2. the operation is atomic, instantly changing the published directory
        # NOTE: it's not easy (possible?) to directly edit the target of a symlink
        os.rename(tmp_link_name, self.publish_dir)
