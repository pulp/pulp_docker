"""
This module contains the code to sync a Docker v1 registry.
"""
import errno
import json
import logging
import os
import shutil
from gettext import gettext as _

from pulp.common.plugins import importer_constants
from pulp.plugins.util import nectar_config
from pulp.plugins.util.publish_step import PluginStep, DownloadStep
from pulp.server.exceptions import MissingValue

from pulp_docker.common import constants, models
from pulp_docker.plugins import registry
from pulp_docker.plugins.importers import sync, tags


_logger = logging.getLogger(__name__)


class SyncStep(PluginStep):
    required_settings = (
        constants.CONFIG_KEY_UPSTREAM_NAME,
        importer_constants.KEY_FEED,
    )

    def __init__(self, repo=None, conduit=None, config=None,
                 working_dir=None):
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
        super(SyncStep, self).__init__(constants.SYNC_STEP_MAIN, repo, conduit, config,
                                       working_dir, constants.IMPORTER_TYPE_ID)
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
        self.index_repository = registry.V1Repository(upstream_name, download_config, url,
                                                      working_dir)

        self.add_child(GetMetadataStep(working_dir=working_dir))
        # save this step so its "units_to_download" attribute can be accessed later
        self.step_get_local_units = sync.GetLocalImagesStep(
            constants.IMPORTER_TYPE_ID, constants.IMAGE_TYPE_ID, ['image_id'], working_dir)
        self.add_child(self.step_get_local_units)
        self.add_child(DownloadStep(constants.SYNC_STEP_DOWNLOAD,
                                    downloads=self.generate_download_requests(),
                                    repo=repo, config=config, working_dir=working_dir,
                                    description=_('Downloading remote files')))
        self.add_child(SaveUnits(working_dir))

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
        for unit_key in self.step_get_local_units.units_to_download:
            image_id = unit_key['image_id']
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

    def sync(self):
        """
        actually initiate the sync

        :return:    a final sync report
        :rtype:     pulp.plugins.model.SyncReport
        """
        self.process_lifecycle()
        return self._build_final_report()


class GetMetadataStep(PluginStep):
    def __init__(self, repo=None, conduit=None, config=None, working_dir=None):
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
        super(GetMetadataStep, self).__init__(constants.SYNC_STEP_METADATA, repo, conduit, config,
                                              working_dir, constants.IMPORTER_TYPE_ID)
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

        # generate unit keys and save them on the parent
        self.parent.available_units = [dict(image_id=i) for i in images_we_need]

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


class SaveUnits(PluginStep):
    def __init__(self, working_dir):
        """
        :param working_dir: full path to the directory into which image files
                            are downloaded. This directory should contain one
                            directory for each docker image, with the ID of the
                            docker image as its name.
        :type  working_dir: basestring
        """
        super(SaveUnits, self).__init__(step_type=constants.SYNC_STEP_SAVE,
                                        plugin_type=constants.IMPORTER_TYPE_ID,
                                        working_dir=working_dir)
        self.description = _('Saving images and tags')

    def process_main(self):
        """
        Gets an iterable of units that were downloaded from the parent step,
        moves their files into permanent storage, and then saves the unit into
        the database and into the repository.
        """
        _logger.debug(self.description)
        for unit_key in self.parent.step_get_local_units.units_to_download:
            image_id = unit_key['image_id']
            with open(os.path.join(self.working_dir, image_id, 'json')) as json_file:
                metadata = json.load(json_file)
            # at least one old docker image did not have a size specified in
            # its metadata
            size = metadata.get('Size')
            # an older version of docker used a lowercase "p"
            parent = metadata.get('parent', metadata.get('Parent'))
            model = models.Image(image_id, parent, size)
            unit = self.get_conduit().init_unit(model.TYPE_ID, model.unit_key, model.unit_metadata,
                                                model.relative_path)

            self.move_files(unit)
            _logger.debug('saving image %s' % image_id)
            self.get_conduit().save_unit(unit)

        _logger.debug('updating tags for repo %s' % self.get_repo().id)
        tags.update_tags(self.get_repo().id, self.parent.tags)

    def move_files(self, unit):
        """
        For the given unit, move all of its associated files from the working
        directory to their permanent location.

        :param unit:    a pulp unit
        :type  unit:    pulp.plugins.model.Unit
        """
        image_id = unit.unit_key['image_id']
        _logger.debug('moving files in to place for image %s' % image_id)
        source_dir = os.path.join(self.working_dir, image_id)
        try:
            os.makedirs(unit.storage_path, mode=0755)
        except OSError, e:
            # it's ok if the directory exists
            if e.errno != errno.EEXIST:
                _logger.error('could not make directory %s' % unit.storage_path)
                raise

        for name in ('json', 'ancestry', 'layer'):
            shutil.move(os.path.join(source_dir, name), os.path.join(unit.storage_path, name))
