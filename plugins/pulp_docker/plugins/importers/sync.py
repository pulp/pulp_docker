"""
This module contains the primary sync entry point for Docker v2 registries.
"""
from gettext import gettext as _
import logging
import os
import shutil

from pulp.common.plugins import importer_constants
from pulp.plugins.util import nectar_config
from pulp.plugins.util.publish_step import PluginStep, DownloadStep, GetLocalUnitsStep
from pulp.server.exceptions import MissingValue

from pulp_docker.common import constants, models
from pulp_docker.plugins import registry
from pulp_docker.plugins.importers import v1_sync


_logger = logging.getLogger(__name__)


class SyncStep(PluginStep):
    """
    This PluginStep is the primary entry point into a repository sync against a Docker v2 registry.
    """
    # The sync will fail if these settings are not provided in the config
    required_settings = (constants.CONFIG_KEY_UPSTREAM_NAME, importer_constants.KEY_FEED)

    def __init__(self, repo=None, conduit=None, config=None,
                 working_dir=None):
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
        :param working_dir: full path to the directory in which transient files
                            should be stored before being moved into long-term
                            storage. This should be deleted by the caller after
                            step processing is complete.
        :type  working_dir: basestring
        """
        super(SyncStep, self).__init__(constants.SYNC_STEP_MAIN, repo, conduit, config,
                                       working_dir, constants.IMPORTER_TYPE_ID)
        self.description = _('Syncing Docker Repository')

        download_config = nectar_config.importer_config_to_nectar_config(config.flatten())
        upstream_name = config.get(constants.CONFIG_KEY_UPSTREAM_NAME)
        url = config.get(importer_constants.KEY_FEED)

        # Create a Repository object to interact with.
        self.index_repository = registry.V2Repository(
            upstream_name, download_config, url, working_dir)
        self.v1_index_repository = registry.V1Repository(upstream_name, download_config, url,
                                                         working_dir)

        v2_found = self.index_repository.api_version_check()
        v1_found = self.v1_index_repository.api_version_check()

        if v2_found:
            _logger.debug(_('v2 API found'))
            self.add_child(V2SyncStep(repo=repo, conduit=conduit, config=config,
                                      working_dir=working_dir))
        if v1_found:
            _logger.debug(_('v1 API found'))
            self.add_child(v1_sync.SyncStep(repo=repo, conduit=conduit, config=config,
                                            working_dir=working_dir))
        if not any((v1_found, v2_found)):
            msg = _('This feed URL is not a Docker v1 or v2 endpoint: %(url)s'.format(url=url))
            _logger.error(msg)
            raise ValueError(msg)

    def sync(self):
        """
        actually initiate the sync

        :return:    a final sync report
        :rtype:     pulp.plugins.model.SyncReport
        """
        self.process_lifecycle()
        return self._build_final_report()


class V2SyncStep(PluginStep):
    """
    This PluginStep is the primary entry point into a repository sync against a Docker v2 registry.
    """
    # The sync will fail if these settings are not provided in the config
    required_settings = (constants.CONFIG_KEY_UPSTREAM_NAME, importer_constants.KEY_FEED)

    def __init__(self, repo=None, conduit=None, config=None,
                 working_dir=None):
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
        :param working_dir: full path to the directory in which transient files
                            should be stored before being moved into long-term
                            storage. This should be deleted by the caller after
                            step processing is complete.
        :type  working_dir: basestring
        """
        super(V2SyncStep, self).__init__(constants.SYNC_STEP_MAIN, repo, conduit, config,
                                         working_dir, constants.IMPORTER_TYPE_ID)
        self.description = _('Syncing Docker Repository')

        self._validate(config)
        download_config = nectar_config.importer_config_to_nectar_config(config.flatten())
        upstream_name = config.get(constants.CONFIG_KEY_UPSTREAM_NAME)
        url = config.get(importer_constants.KEY_FEED)
        # The GetMetadataStep will set this to a list of dictionaries of the form
        # {'digest': digest}.
        self.available_units = []

        # Create a Repository object to interact with.
        self.index_repository = registry.V2Repository(
            upstream_name, download_config, url, working_dir)
        # We'll attempt to use a V2Repository's API version check call to find out if it is a V2
        # registry. This will raise a NotImplementedError if url is not determined to be a Docker v2
        # registry.
        self.index_repository.api_version_check()
        self.step_get_metadata = GetMetadataStep(repo=repo, conduit=conduit, config=config,
                                                 working_dir=working_dir)
        self.add_child(self.step_get_metadata)
        # save this step so its "units_to_download" attribute can be accessed later
        self.step_get_local_units = GetLocalBlobsStep(
            constants.IMPORTER_TYPE_ID, models.Blob.TYPE_ID, ['digest'], self.working_dir)
        self.add_child(self.step_get_local_units)
        self.add_child(
            DownloadStep(
                constants.SYNC_STEP_DOWNLOAD, downloads=self.generate_download_requests(),
                repo=self.repo, config=self.config, working_dir=self.working_dir,
                description=_('Downloading remote files')))
        self.add_child(SaveUnitsStep(self.working_dir))

    def generate_download_requests(self):
        """
        a generator that yields DownloadRequest objects based on which units
        were determined to be needed. This looks at the GetLocalUnits step's
        output, which includes a list of units that need their files downloaded.

        :return:    generator of DownloadRequest instances
        :rtype:     types.GeneratorType
        """
        for unit_key in self.step_get_local_units.units_to_download:
            digest = unit_key['digest']
            yield self.index_repository.create_blob_download_request(digest,
                                                                     self.get_working_dir())

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


class GetMetadataStep(PluginStep):
    """
    This step gets the Docker metadata from a Docker registry.
    """
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
        # Map manifest digests to Manifest objects
        self.manifests = {}

        self.add_child(DownloadManifestsStep(repo, conduit, config, working_dir))
        self.step_get_local_units = GetLocalManifestsStep(
            constants.IMPORTER_TYPE_ID, models.Manifest.TYPE_ID, ['digest'], working_dir)
        self.add_child(self.step_get_local_units)

    @property
    def available_units(self):
        """
        Return the unit keys as found in self.manifests.

        :return: A list of unit keys
        :rtype:  list
        """
        return [m.unit_key for k, m in self.manifests.items()]


class DownloadManifestsStep(PluginStep):
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
        super(DownloadManifestsStep, self).__init__(constants.SYNC_STEP_METADATA, repo, conduit,
                                                    config, working_dir, constants.IMPORTER_TYPE_ID)
        self.description = _('Downloading manifests')

    def process_main(self):
        """
        Determine which manifests and blobs are available upstream, get the upstream tags, and
        save a list of available unit keys and manifests on the SyncStep.
        """
        super(DownloadManifestsStep, self).process_main()
        _logger.debug(self.description)

        available_tags = self.parent.parent.index_repository.get_tags()
        available_blobs = set()
        for tag in available_tags:
            digest, manifest = self.parent.parent.index_repository.get_manifest(tag)
            # Save the manifest to the working directory
            with open(os.path.join(self.working_dir, digest), 'w') as manifest_file:
                manifest_file.write(manifest)
            manifest = models.Manifest.from_json(manifest, digest)
            self.parent.manifests[digest] = manifest
            for layer in manifest.fs_layers:
                available_blobs.add(layer['blobSum'])

        # Update the available units with the blobs we learned about
        available_blobs = [{'digest': d} for d in available_blobs]
        self.parent.parent.available_units.extend(available_blobs)


class GetLocalBlobsStep(GetLocalUnitsStep):
    def _dict_to_unit(self, unit_dict):
        """
        convert a unit dictionary (a flat dict that has all unit key, metadata,
        etc. keys at the root level) into a Unit object. This requires knowing
        not just what fields are part of the unit key, but also how to derive
        the storage path.

        Any keys in the "metadata" dict on the returned unit will overwrite the
        corresponding values that are currently saved in the unit's metadata. In
        this case, we pass an empty dict, because we don't want to make changes.

        :param unit_dict:   a flat dictionary that has all unit key, metadata,
                            etc. keys at the root level, representing a unit
                            in pulp
        :type  unit_dict:   dict

        :return:    a unit instance
        :rtype:     pulp.plugins.model.Unit
        """
        model = models.Blob(unit_dict['digest'])
        return self.get_conduit().init_unit(model.TYPE_ID, model.unit_key, {},
                                            model.relative_path)


class GetLocalManifestsStep(GetLocalUnitsStep):
    """
    Get the manifests we have locally and ensure that they are associated with the repository.
    """
    def _dict_to_unit(self, unit_dict):
        """
        convert a unit dictionary (a flat dict that has all unit key, metadata,
        etc. keys at the root level) into a Unit object. This requires knowing
        not just what fields are part of the unit key, but also how to derive
        the storage path.

        Any keys in the "metadata" dict on the returned unit will overwrite the
        corresponding values that are currently saved in the unit's metadata. In
        this case, we pass an empty dict, because we don't want to make changes.

        :param unit_dict:   a flat dictionary that has all unit key, metadata,
                            etc. keys at the root level, representing a unit
                            in pulp
        :type  unit_dict:   dict

        :return:    a unit instance
        :rtype:     pulp.plugins.model.Unit
        """
        model = self.parent.parent.step_get_metadata.manifests[unit_dict['digest']]
        return self.get_conduit().init_unit(model.TYPE_ID, model.unit_key, model.metadata,
                                            model.relative_path)


class SaveUnitsStep(PluginStep):
    def __init__(self, working_dir):
        """
        :param working_dir: full path to the directory into which blob files
                            are downloaded. This directory should contain one
                            directory for each docker blob, with the ID of the
                            docker blob as its name.
        :type  working_dir: basestring
        """
        super(SaveUnitsStep, self).__init__(
            step_type=constants.SYNC_STEP_SAVE, plugin_type=constants.IMPORTER_TYPE_ID,
            working_dir=working_dir)
        self.description = _('Saving manifests and blobs')

    def process_main(self):
        """
        Gets an iterable of units that were downloaded from the parent step,
        moves their files into permanent storage, and then saves the unit into
        the database and into the repository.
        """
        _logger.debug(self.description)
        # Save the Manifests
        for unit_key in self.parent.step_get_metadata.step_get_local_units.units_to_download:
            model = self.parent.step_get_metadata.manifests[unit_key['digest']]
            unit = self.get_conduit().init_unit(model.TYPE_ID, model.unit_key, model.metadata,
                                                model.relative_path)
            self._move_file(unit)
            _logger.debug('saving manifest %s' % model.digest)
            self.get_conduit().save_unit(unit)

        # Save the Blobs
        for unit_key in self.parent.step_get_local_units.units_to_download:
            model = models.Blob(unit_key['digest'])
            unit = self.get_conduit().init_unit(model.TYPE_ID, model.unit_key, model.metadata,
                                                model.relative_path)
            self._move_file(unit)
            _logger.debug('saving Blob %s' % unit_key)
            self.get_conduit().save_unit(unit)

    def _move_file(self, unit):
        """
        For the given unit, move its associated file from the working
        directory to its permanent location.

        :param unit: a pulp unit
        :type  unit: pulp.plugins.model.Unit
        """
        _logger.debug('moving files in to place for Unit {unit}'.format(unit=unit))
        shutil.move(os.path.join(self.working_dir, unit.unit_key['digest']), unit.storage_path)
