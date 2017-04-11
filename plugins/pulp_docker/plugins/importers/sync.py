"""
This module contains the primary sync entry point for Docker v2 registries.
"""
from gettext import gettext as _
import errno
import httplib
import itertools
import logging
import os
import signal

from mongoengine import NotUniqueError

from pulp.common.plugins import importer_constants
from pulp.plugins.util import nectar_config, publish_step
from pulp.server.controllers import repository
from pulp.server.exceptions import MissingValue, PulpCodedException

from pulp_docker.common import constants, error_codes
from pulp_docker.plugins import models, registry, token_util
from pulp_docker.plugins.importers import v1_sync


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

        # Unit keys, populated by v1_sync.GetMetadataStep
        self.v1_available_units = []
        # populated by v1_sync.GetMetadataStep
        self.v1_tags = {}

        # Create a Repository object to interact with.
        self.index_repository = registry.V2Repository(
            upstream_name, download_config, url, self.get_working_dir())
        self.v1_index_repository = registry.V1Repository(upstream_name, download_config, url,
                                                         self.get_working_dir())

        # determine which API versions are supported and add corresponding steps
        v2_enabled = config.get(constants.CONFIG_KEY_ENABLE_V2, default=True)
        v1_enabled = config.get(constants.CONFIG_KEY_ENABLE_V1, default=False)
        if not v2_enabled:
            _logger.debug(_('v2 API skipped due to config'))
        if not v1_enabled:
            _logger.debug(_('v1 API skipped due to config'))
        v2_found = v2_enabled and self.index_repository.api_version_check()
        v1_found = v1_enabled and self.v1_index_repository.api_version_check()
        if v2_found:
            _logger.debug(_('v2 API found'))
            self.add_v2_steps(repo, conduit, config)
        if v1_found:
            _logger.debug(_('v1 API found'))
            self.add_v1_steps(repo, config)
        if not any((v1_found, v2_found)):
            raise PulpCodedException(error_code=error_codes.DKR1008, registry=url)

    def add_v2_steps(self, repo, conduit, config):
        """
        Add v2 sync steps.

        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param conduit:     sync conduit to use
        :type  conduit:     pulp.plugins.conduits.repo_sync.RepoSyncConduit
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
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
            TokenAuthDownloadStep(
                step_type=constants.SYNC_STEP_DOWNLOAD, downloads=self.generate_download_requests(),
                repo=self.repo, config=self.config, description=_('Downloading remote files')))
        self.add_child(SaveUnitsStep())
        self.save_tags_step = SaveTagsStep()
        self.add_child(self.save_tags_step)

    def add_v1_steps(self, repo, config):
        """
        Add v1 sync steps.

        :param repo:        repository to sync
        :type  repo:        pulp.plugins.model.Repository
        :param config:      config object for the sync
        :type  config:      pulp.plugins.config.PluginCallConfiguration
        """
        self.add_child(v1_sync.GetMetadataStep())
        # save this step so its "units_to_download" attribute can be accessed later
        self.v1_step_get_local_units = publish_step.GetLocalUnitsStep(
            constants.IMPORTER_TYPE_ID, available_units=self.v1_available_units)
        self.v1_step_get_local_units.step_id = constants.SYNC_STEP_GET_LOCAL_V1
        self.add_child(self.v1_step_get_local_units)
        self.add_child(publish_step.DownloadStep(
            constants.SYNC_STEP_DOWNLOAD_V1, downloads=self.v1_generate_download_requests(),
            repo=repo, config=config, description=_('Downloading remote files')))
        self.add_child(v1_sync.SaveImages())

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

    def v1_generate_download_requests(self):
        """
        a generator that yields DownloadRequest objects based on which units
        were determined to be needed. This looks at the GetLocalUnits step's
        output, which includes a list of units that need their files downloaded.

        :return:    generator of DownloadRequest instances
        :rtype:     types.GeneratorType
        """
        for unit in self.v1_step_get_local_units.units_to_download:
            destination_dir = os.path.join(self.get_working_dir(), unit.image_id)
            try:
                os.makedirs(destination_dir, mode=0755)
            except OSError, e:
                # it's ok if the directory exists
                if e.errno != errno.EEXIST:
                    raise
            # we already retrieved the ancestry files for the tagged images, so
            # some of these will already exist
            if not os.path.exists(os.path.join(destination_dir, 'ancestry')):
                yield self.v1_index_repository.create_download_request(unit.image_id, 'ancestry',
                                                                       destination_dir)

            yield self.v1_index_repository.create_download_request(unit.image_id, 'json',
                                                                   destination_dir)
            yield self.v1_index_repository.create_download_request(unit.image_id, 'layer',
                                                                   destination_dir)

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
        self.total_units = len(available_tags)
        upstream_name = self.config.get('upstream_name')
        for tag in available_tags:
            manifests = self.parent.index_repository.get_manifest(tag)
            for manifest in manifests:
                manifest, digest = manifest
                manifest = self._process_manifest(manifest, digest, tag, upstream_name,
                                                  available_blobs)
                if manifest.config_layer:
                    available_blobs.add(manifest.config_layer)
                self.progress_successes += 1
        # Update the available units with the Manifests and Blobs we learned about
        available_blobs = [models.Blob(digest=d) for d in available_blobs]
        self.parent.available_blobs.extend(available_blobs)

    def _process_manifest(self, manifest, digest, tag, upstream_name, available_blobs):
        """
        Process manifest.

        :param manifest: manifest details
        :type  manifest: basestring
        :param digest: Digest of the manifest to be processed
        :type digest: basesting
        :param tag: Tag which the manifest references
        :type tag: basestring
        :param upstream_name: Upstream name of the repository
        :type upstream_name: basestring
        :param available_blobs: set of current available blobs accumulated dusring sync
        :type available_blobs: set

        :return: An initialized Manifest object
        :rtype: pulp_docker.plugins.models.Manifest

        """

        # Save the manifest to the working directory
        with open(os.path.join(self.get_working_dir(), digest), 'w') as manifest_file:
            manifest_file.write(manifest)
        manifest = models.Manifest.from_json(manifest, digest, tag, upstream_name)
        self.parent.available_manifests.append(manifest)
        for layer in manifest.fs_layers:
            available_blobs.add(layer.blob_sum)
        # Remember this tag for the SaveTagsStep.
        self.parent.save_tags_step.tagged_manifests.append((tag, manifest))

        return manifest


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
        return iter(itertools.chain(self.parent.step_get_local_blobs.units_to_download,
                                    self.parent.step_get_local_manifests.units_to_download))

    def process_main(self, item):
        """
        This method gets called with each Unit that was downloaded from the parent step. It moves
        each Unit's files into permanent storage, and saves each Unit into the database and into the
        repository.

        :param item: The Unit to save in Pulp.
        :type  item: pulp.server.db.model.FileContentUnit
        """
        item.set_storage_path(item.digest)
        try:
            item.save_and_import_content(os.path.join(self.get_working_dir(), item.digest))
        except NotUniqueError:
            item = item.__class__.objects.get(**item.unit_key)
        repository.associate_single_unit(self.get_repo().repo_obj, item)


class SaveTagsStep(publish_step.SaveUnitsStep):
    """
    Create or update Tag objects to reflect the tags that we found during the sync.
    """
    def __init__(self):
        """
        Initialize the step, setting its description.
        """
        super(SaveTagsStep, self).__init__(step_type=constants.SYNC_STEP_SAVE)
        self.description = _('Saving Tags')
        # This list contains tuple of (tag, manifest)
        self.tagged_manifests = []

    def process_main(self):
        """
        For each tag found in the remote repository, if a Tag object exists in this repository we
        need to make sure its manifest_digest attribute points at this Manifest. If not, we need to
        create one. We'll rely on the uniqueness constraint in MongoDB to allow us to try to create
        it, and if that fails we'll fall back to updating the existing one.
        """
        self.total_units = len(self.tagged_manifests)
        for tag, manifest in self.tagged_manifests:
            new_tag = models.Tag.objects.tag_manifest(repo_id=self.get_repo().repo_obj.repo_id,
                                                      tag_name=tag, manifest_digest=manifest.digest,
                                                      schema_version=manifest.schema_version)
            if new_tag:
                repository.associate_single_unit(self.get_repo().repo_obj, new_tag)
                self.progress_successes += 1


class TokenAuthDownloadStep(publish_step.DownloadStep):
    """
    Download remote files. For v2, this may require a bearer token to be used. This step attempts
    to download files, and if it fails due to a 401, it will retrieve the auth token and retry the
    download.
    """

    def __init__(self, step_type, downloads=None, repo=None, conduit=None, config=None,
                 working_dir=None, plugin_type=None, description=''):
        """
        Initialize the step, setting its description.
        """

        # Even if basic auth is enabled, it should only be used for the token requests which are
        # handled by the parent's token_downloader.
        config.repo_plugin_config.pop(importer_constants.KEY_BASIC_AUTH_USER, None)
        config.repo_plugin_config.pop(importer_constants.KEY_BASIC_AUTH_PASS, None)
        super(TokenAuthDownloadStep, self).__init__(
            step_type, downloads=downloads, repo=repo, conduit=conduit, config=config,
            working_dir=working_dir, plugin_type=plugin_type)
        self.description = _('Downloading remote files')
        self.token = None
        self._requests_map = {}

    def process_main(self, item=None):
        """
        Allow request objects to be available after a download fails.
        """
        for request in self.downloads:
            self._requests_map[request.url] = request
        super(TokenAuthDownloadStep, self).process_main(item)

    def download_failed(self, report):
        """
        If the download is unauthorized, attempt to retreive a token and try again.

        :param report: download report
        :type  report: nectar.report.DownloadReport
        """
        if report.error_report.get('response_code') == httplib.UNAUTHORIZED:
            _logger.debug(_('Download unauthorized, attempting to retrieve a token.'))
            request = self._requests_map[report.url]
            token = token_util.request_token(self.parent.index_repository.token_downloader,
                                             request, report.headers)
            self.downloader.session.headers = token_util.update_auth_header(
                self.downloader.session.headers, token)
            _logger.debug("Trying download again with new bearer token.")
            # Events must be false or download_failed will recurse
            report = self.downloader.download_one(request, events=False)
        if report.state is report.DOWNLOAD_SUCCEEDED:
            self.download_succeeded(report)
        elif report.state is report.DOWNLOAD_FAILED:
            super(TokenAuthDownloadStep, self).download_failed(report)
            # Docker blobs have ancestry relationships and need all blobs to function. Sync should
            # stop immediately to prevent publishing of an incomplete repository.
            os.kill(os.getpid(), signal.SIGKILL)
