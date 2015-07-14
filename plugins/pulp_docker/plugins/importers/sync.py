import errno
from gettext import gettext as _
import json
import logging
import os

from pulp.common.plugins import importer_constants
from pulp.plugins.util import nectar_config
from pulp.plugins.util.publish_step import PluginStep, DownloadStep, \
    GetLocalUnitsStep, SaveUnitsStep
from pulp.server.controllers import repository as repo_controller
from pulp.server.exceptions import MissingValue
from pulp.server.db import model as platform_models

from pulp_docker.common import constants, tags
from pulp_docker.plugins.registry import Repository
from pulp_docker.plugins.db import models


_logger = logging.getLogger(__name__)


class SyncStep(PluginStep):
    required_settings = (
        constants.CONFIG_KEY_UPSTREAM_NAME,
        importer_constants.KEY_FEED,
    )

    def __init__(self, repo=None, conduit=None, config=None, **kwargs):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
        super(SyncStep, self).__init__(constants.SYNC_STEP_MAIN,
                                       repo=repo, conduit=conduit,
                                       config=config, plugin_type=constants.IMPORTER_TYPE_ID,
                                       **kwargs)
        self.description = _('Syncing Docker Repository')

        # Unit keys, populated by GetMetadataStep
        self.available_units = []
        # populated by GetMetadataStep
        self.tags = {}

        self.validate(config)
        download_config = nectar_config.importer_config_to_nectar_config(config.flatten())
        upstream_name = config.get(constants.CONFIG_KEY_UPSTREAM_NAME)
        url = config.get(importer_constants.KEY_FEED)

        # create a Repository object to interact with
        self.index_repository = Repository(upstream_name, download_config, url,
                                           self.get_working_dir())

        self.add_child(GetMetadataStep())
        # save this step so its "units_to_download" attribute can be accessed later
        self.step_get_local_units = GetLocalUnitsStep(constants.IMPORTER_TYPE_ID)
        self.add_child(self.step_get_local_units)
        self.add_child(DownloadStep(constants.SYNC_STEP_DOWNLOAD,
                                    downloads=self.generate_download_requests(),
                                    repo=repo, config=config,
                                    description=_('Downloading remote files')))
        self.add_child(SaveDockerUnits())

    @classmethod
    def validate(cls, config):
        """
        Ensure that any required settings have non-empty values.

        :param config:  config object for the sync
        :type  config:  pulp.plugins.config.PluginCallConfiguration

        :raises MissingValue:   if any required sync setting is missing
        """
        missing = []
        for key in cls.required_settings:
            if not config.get(key):
                missing.append(key)

        if missing:
            raise MissingValue(missing)

    def generate_download_requests(self):
        """
        a generator that yields DownloadRequest objects based on which units
        were determined to be needed. This looks at the GetLocalUnits step's
        output, which includes a list of units that need their files downloaded.

        :return:    generator of DownloadRequest instances
        :rtype:     types.GeneratorType
        """
        for unit in self.step_get_local_units.units_to_download:
            image_id = unit.image_id
            destination_dir = os.path.join(self.get_working_dir(), image_id)
            try:
                os.makedirs(destination_dir, mode=0755)
            except OSError, e:
                # it's ok if the directory exists
                if e.errno != errno.EEXIST:
                    raise
            # we already retrieved the ancestry files for the tagged images, so
            # some of these will already exist
            if not os.path.exists(os.path.join(destination_dir, 'ancestry')):
                yield self.index_repository.create_download_request(image_id, 'ancestry',
                                                                    destination_dir)

            yield self.index_repository.create_download_request(image_id, 'json', destination_dir)
            yield self.index_repository.create_download_request(image_id, 'layer', destination_dir)


class GetMetadataStep(PluginStep):
    def __init__(self, repo=None, conduit=None, config=None, **kwargs):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        :param working_dir: full path to the directory in which transient files
                            should be stored before being moved into long-term
                            storage. This should be deleted by the caller after
                            step processing is complete.
        :type  working_dir: basestring
        """
        super(GetMetadataStep, self).__init__(constants.SYNC_STEP_METADATA,
                                              repo=repo, conduit=conduit, config=config, **kwargs)
        self.description = _('Retrieving metadata')

    def process_main(self):
        """
        determine what images are available upstream, get the upstream tags, and
        save a list of available unit keys on the parent step
        """
        super(GetMetadataStep, self).process_main()
        download_dir = self.get_working_dir()
        _logger.debug(self.description)

        # determine what images are available by querying the upstream source
        available_images = self.parent.index_repository.get_image_ids()
        # get remote tags and save them on the parent
        self.parent.tags.update(self.parent.index_repository.get_tags())
        # transform the tags so they contain full image IDs instead of abbreviations
        self.expand_tag_abbreviations(available_images, self.parent.tags)

        tagged_image_ids = self.parent.tags.values()

        # retrieve ancestry files and then parse them to determine the full
        # collection of upstream images that we should ensure are obtained.
        self.parent.index_repository.get_ancestry(tagged_image_ids)
        images_we_need = set(tagged_image_ids)
        for image_id in tagged_image_ids:
            images_we_need.update(set(self.find_and_read_ancestry_file(image_id, download_dir)))

        # Generate the DockerImage objects and save them on the parent
        self.parent.available_units = [models.DockerImage(image_id=i) for i in images_we_need]

    @staticmethod
    def expand_tag_abbreviations(image_ids, tags):
        """
        Given a list of full image IDs and a dictionary of tags, where the values
        are either image IDs or abbreviated image IDs, this function replaces
        abbreviated image IDs in the tags dictionary with full IDs. Changes are
        applied in-place to the passed-in dictionary.

        This algorithm will not scale well, but it's unlikely we'll ever see
        n>100, let alone a scale where this algorithm would become a bottleneck.
        For such small data sets, a fancier and more efficient algorithm would
        require enough setup and custom data structures, that the overhead might
        often outweigh any gains.

        :param image_ids:   list of image IDs
        :type  image_ids:   list
        :param tags:        dictionary where keys are tag names and values are
                            either full image IDs or abbreviated image IDs.
        """
        for tag_name, abbreviated_id in tags.items():
            for image_id in image_ids:
                if image_id.startswith(abbreviated_id):
                    tags[tag_name] = image_id
                    break

    @staticmethod
    def find_and_read_ancestry_file(image_id, parent_dir):
        """
        Given an image ID, find it's file directory in the given parent directory
        (it will be a directory whose name in the image_id), open the "ancestry"
        file within it, deserialize its contents as json, and return the result.

        :param image_id:    unique ID of a docker image
        :type  image_id:    basestring
        :param parent_dir:  full path to the parent directory in which we should
                            look for a directory whose name is the image_id
        :type  parent_dir:  basestring

        :return:    list of image_ids that represent the ancestry for the image ID
        :rtype:     list
        """
        with open(os.path.join(parent_dir, image_id, 'ancestry')) as ancestry_file:
            return json.load(ancestry_file)


class SaveDockerUnits(SaveUnitsStep):

    def __init__(self, step_type=constants.SYNC_STEP_SAVE):
        super(SaveDockerUnits, self).__init__(step_type=step_type)
        self.description = _('Saving images and tags')

    def get_iterator(self):
        """
        This method returns an iterator to loop over items.
        The items created by this iterator will be iterated over by the process_main method.

        :return: a list or other iterable
        :rtype: iterator of pulp_docker.plugins.db.models.DockerImage
        """
        # Return a generator so that the platform will show a returned value
        # if this returns an empty list the platform will call process_main once with item=none
        return iter(self.parent.step_get_local_units.units_to_download)

    def process_main(self, item=None):
        """
        Associate an individual docker image with our repository

        :param item: The individual docker image to associate to a repository
        :type item: pulp_docker.plugins.db.models.DockerImage
        """
        self._associate_item(item)

    def _associate_item(self, item):
        """
        Associate an individual docker image with our repository

        This is in a separate method from process_main so that subclasses can mock it out
        with their testing.

        :param item: The individual docker image to associate to a repository
        :type item: pulp_docker.plugins.db.models.DockerImage
        """
        image_id = item.image_id
        with open(os.path.join(self.get_working_dir(), image_id, 'json')) as json_file:
            metadata = json.load(json_file)
        # at least one old docker image did not have a size specified in
        # its metadata
        size = metadata.get('Size')
        # an older version of docker used a lowercase "p"
        parent = metadata.get('parent', metadata.get('Parent'))
        item.parent_id = parent
        item.size = size
        item.set_content(os.path.join(self.get_working_dir(), image_id))

        item.save()
        repo_controller.associate_single_unit(self.get_repo(), item)

    def finalize(self):
        """
        Method called to finalize after process_main has been called.  This will
        be called even if process_main or initialize raises an exceptions
        """
        super(SaveDockerUnits, self).finalize()
        # Get an updated copy of the repo so that we can update the tags
        repo = self.get_repo()
        _logger.debug('updating tags for repo {repo_id}'.format(repo_id=repo.repo_id))
        if self.parent.tags:
            new_tags = tags.generate_updated_tags(repo.scratchpad, self.parent.tags)
            platform_models.Repository.objects(repo_id=repo.repo_id).\
                update_one(set__scratchpad__tags=new_tags)
