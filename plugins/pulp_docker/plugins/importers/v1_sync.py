"""
This module contains the code to sync a Docker v1 registry.
"""
import json
import logging
import os
from gettext import gettext as _

from mongoengine import NotUniqueError
from pulp.plugins.util.publish_step import PluginStep, SaveUnitsStep
from pulp.server.controllers import repository as repo_controller
from pulp.server.db import model as platform_models

from pulp_docker.common import constants, tags
from pulp_docker.plugins import models


_logger = logging.getLogger(__name__)


class GetMetadataStep(PluginStep):
    def __init__(self, repo=None, conduit=None, config=None):
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
        super(GetMetadataStep, self).__init__(
            step_type=constants.SYNC_STEP_METADATA_V1, repo=repo, conduit=conduit, config=config,
            plugin_type=constants.IMPORTER_TYPE_ID)
        self.description = _('Retrieving v1 metadata')

    def process_main(self):
        """
        determine what images are available upstream, get the upstream tags, and
        save a list of available unit keys on the parent step
        """
        super(GetMetadataStep, self).process_main()
        download_dir = self.get_working_dir()
        _logger.debug(self.description)

        # determine what images are available by querying the upstream source
        available_images = self.parent.v1_index_repository.get_image_ids()
        # get remote tags and save them on the parent
        self.parent.v1_tags.update(self.parent.v1_index_repository.get_tags())
        # transform the tags so they contain full image IDs instead of abbreviations
        self.expand_tag_abbreviations(available_images, self.parent.v1_tags)

        tagged_image_ids = self.parent.v1_tags.values()

        # retrieve ancestry files and then parse them to determine the full
        # collection of upstream images that we should ensure are obtained.
        self.parent.v1_index_repository.get_ancestry(tagged_image_ids)
        images_we_need = set(tagged_image_ids)
        for image_id in tagged_image_ids:
            images_we_need.update(set(self.find_and_read_ancestry_file(image_id, download_dir)))

        # generate Images and store them on the parent
        self.parent.v1_available_units.extend(models.Image(image_id=i) for i in images_we_need)

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


class SaveImages(SaveUnitsStep):
    def __init__(self, step_type=constants.SYNC_STEP_SAVE_V1):
        """
        Initialize the SaveImages Step, setting its type and description.
        """
        super(SaveImages, self).__init__(step_type=step_type)
        self.description = _('Saving v1 images and tags')

    def get_iterator(self):
        """
        This method returns an iterator that traverses the list of Images that were downloaded.

        :return: a list or other iterable
        :rtype:  iterator of pulp_docker.plugins.models.Image
        """
        return iter(self.parent.v1_step_get_local_units.units_to_download)

    def process_main(self, item):
        """
        This method gets called with each Unit that was downloaded from the parent step. It moves
        each Unit's files into permanent storage, and saves each Unit into the database and into the
        repository.

        :param item: The Image to save in Pulp
        :type  item: pulp_docker.plugins.models.Image
        """
        with open(os.path.join(self.get_working_dir(), item.image_id, 'json')) as json_file:
            metadata = json.load(json_file)
        # at least one old docker image did not have a size specified in
        # its metadata
        size = metadata.get('Size')
        # an older version of docker used a lowercase "p"
        parent = metadata.get('parent', metadata.get('Parent'))
        item.parent_id = parent
        item.size = size

        try:
            item.save()
        except NotUniqueError:
            item = item.__class__.objects.get(**item.unit_key)
        else:
            tmp_dir = os.path.join(self.get_working_dir(), item.image_id)
            for name in os.listdir(tmp_dir):
                path = os.path.join(tmp_dir, name)
                item.safe_import_content(path, location=os.path.basename(path))

        repo_controller.associate_single_unit(self.get_repo().repo_obj, item)

    def finalize(self):
        """
        Update the tags on the repository object. This method is called after process_main has been
        called. This will be called even if process_main or initialize raises an exceptions.
        """
        super(SaveImages, self).finalize()
        # Get an updated copy of the repo so that we can update the tags
        repo = self.get_repo().repo_obj
        _logger.debug('updating v1 tags for repo {repo_id}'.format(repo_id=repo.repo_id))
        if self.parent.v1_tags:
            new_tags = tags.generate_updated_tags(repo.scratchpad, self.parent.v1_tags)
            platform_models.Repository.objects(repo_id=repo.repo_id).\
                update_one(set__scratchpad__tags=new_tags)
