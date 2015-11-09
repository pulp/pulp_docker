"""
This module contains the primary sync entry point for Docker v2 registries.
"""
from gettext import gettext as _
import itertools
import logging
import os

from pulp.common.plugins import importer_constants
from pulp.plugins.util import nectar_config, publish_step
from pulp.server.controllers import repository
from pulp.server.exceptions import MissingValue

from pulp_docker.common import constants
from pulp_docker.plugins import models, registry


_logger = logging.getLogger(__name__)


class SyncStep(publish_step.PluginStep):
    """
    This PluginStep is the primary entry point into a repository sync against a Docker v2 registry.
    """
    # The sync will fail if these settings are not provided in the config
    required_settings = (constants.CONFIG_KEY_UPSTREAM_NAME, importer_constants.KEY_FEED)

    def __init__(self, repo=None, conduit=None, config=None):
        """
        This method initializes the SyncStep. It first validates the config to ensure that the
        required keys are present. It then constructs some needed items (such as a download config),
        and determines whether the feed URL is a Docker v2 registry or not. If it is, it
        instantiates child tasks that are appropriate for syncing a v2 registry, and if it is not it
        raises a NotImplementedError.

        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
        super(SyncStep, self).__init__(
            step_type=constants.SYNC_STEP_MAIN, repo=repo, conduit=conduit, config=config,
            plugin_type=constants.IMPORTER_TYPE_ID)
        self.description = _('Syncing Docker Repository')

        self._validate(config)
        download_config = nectar_config.importer_config_to_nectar_config(config.flatten())
        upstream_name = config.get(constants.CONFIG_KEY_UPSTREAM_NAME)
        url = config.get(importer_constants.KEY_FEED)
        # The DownloadMetadataSteps will set these to a list of Manifests and Blobs
        self.available_manifests = []
        self.available_blobs = []

        # Create a Repository object to interact with.
        self.index_repository = registry.V2Repository(
            upstream_name, download_config, url, self.get_working_dir())
        # We'll attempt to use a V2Repository's API version check call to find out if it is a V2
        # registry. This will raise a NotImplementedError if url is not determined to be a Docker v2
        # registry.
        self.index_repository.api_version_check()
        self.add_child(DownloadManifestsStep(repo=repo, conduit=conduit, config=config))
        # save these steps so their "units_to_download" attributes can be accessed later. We want
        # them to be separate steps because we have already downloaded all the Manifests but should
        # only save the new ones, while needing to go download the missing Blobs. Thus they must be
        # handled separately.
        self.step_get_local_manifests = publish_step.GetLocalUnitsStep(
            importer_type=constants.IMPORTER_TYPE_ID, available_units=self.available_manifests)
        self.step_get_local_blobs = publish_step.GetLocalUnitsStep(
            importer_type=constants.IMPORTER_TYPE_ID, available_units=self.available_blobs)
        self.add_child(self.step_get_local_manifests)
        self.add_child(self.step_get_local_blobs)
        self.add_child(
            publish_step.DownloadStep(
                step_type=constants.SYNC_STEP_DOWNLOAD, downloads=self.generate_download_requests(),
                repo=self.repo, config=self.config, description=_('Downloading remote files')))
        self.add_child(SaveUnitsStep())

    def generate_download_requests(self):
        """
        a generator that yields DownloadRequest objects based on which units
        were determined to be needed. This looks at the GetLocalUnits step's
        output, which includes a list of units that need their files downloaded.

        :return:    generator of DownloadRequest instances
        :rtype:     types.GeneratorType
        """
        for unit in self.step_get_local_blobs.units_to_download:
            yield self.index_repository.create_blob_download_request(unit.digest)

    @classmethod
    def _validate(cls, config):
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


class DownloadManifestsStep(publish_step.PluginStep):
    def __init__(self, repo=None, conduit=None, config=None):
        """
        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
        super(DownloadManifestsStep, self).__init__(
            step_type=constants.SYNC_STEP_METADATA, repo=repo, conduit=conduit, config=config,
            plugin_type=constants.IMPORTER_TYPE_ID)
        self.description = _('Downloading manifests')

    def process_main(self):
        """
        Determine which manifests and blobs are available upstream, get the upstream tags, and
        save a list of available unit keys and manifests on the SyncStep.
        """
        super(DownloadManifestsStep, self).process_main()
        _logger.debug(self.description)

        available_tags = self.parent.index_repository.get_tags()
        # This will be a set of Blob digests. The set is used because they can be repeated and we
        # only want to download each layer once.
        available_blobs = set()
        for tag in available_tags:
            digest, manifest = self.parent.index_repository.get_manifest(tag)
            # Save the manifest to the working directory
            with open(os.path.join(self.get_working_dir(), digest), 'w') as manifest_file:
                manifest_file.write(manifest)
            manifest = models.Manifest.from_json(manifest, digest)
            self.parent.available_manifests.append(manifest)
            for layer in manifest.fs_layers:
                available_blobs.add(layer.blob_sum)

        # Update the available units with the Manifests and Blobs we learned about
        available_blobs = [models.Blob(digest=d) for d in available_blobs]
        self.parent.available_blobs.extend(available_blobs)


class SaveUnitsStep(publish_step.SaveUnitsStep):
    """
    Save the Units that need to be added to the repository and move them to the content folder.
    """
    def __init__(self):
        """
        Initialize the step, setting its description.
        """
        super(SaveUnitsStep, self).__init__(step_type=constants.SYNC_STEP_SAVE)
        self.description = _('Saving Manifests and Blobs')

    def get_iterator(self):
        """
        Return an iterator that will traverse the list of Units that were downloaded.

        :return: An iterable containing the Blobs and Manifests that were downloaded and are new to
                 Pulp.
        :rtype:  iterator
        """
        return iter(itertools.chain(self.parent.step_get_local_manifests.units_to_download,
                                    self.parent.step_get_local_blobs.units_to_download))

    def process_main(self, item):
        """
        This method gets called with each Unit that was downloaded from the parent step. It moves
        each Unit's files into permanent storage, and saves each Unit into the database and into the
        repository.

        :param item: The Unit to save in Pulp.
        :type  item: pulp.server.db.model.FileContentUnit
        """
        item.set_content(os.path.join(self.get_working_dir(), item.digest))
        item.save()
        repository.associate_single_unit(self.get_repo(), item)
