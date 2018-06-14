from gettext import gettext as _
import json
import os

import mongoengine
from pulp.common import dateutils
from pulp.plugins.util import misc, publish_step
from pulp.plugins.rsync.publish import Publisher, RSyncPublishStep
from pulp.plugins.util.publish_step import RSyncFastForwardUnitPublishStep
from pulp.server.db.model import Distributor

from pulp_docker.common import constants
from pulp_docker.plugins import models
from pulp_docker.plugins.distributors import configuration, v1_publish_steps


class WebPublisher(publish_step.PublishStep):
    """
    Docker Web publisher class that is responsible for the actual publishing
    of a docker repository via a web server. It will publish the repository with v1 code and v2
    code.
    """

    def __init__(self, repo, publish_conduit, config):
        """
        Initialize the WebPublisher, adding the V1 and V2 publishers as its children. The V1
        publisher will publish any Image units found in the repository, and the V2 publisher will
        publish any Manifests and Blobs it finds in the repository.

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

        predistributor = self.get_predistributor()
        if predistributor:
            end_date = predistributor["last_publish"]
            if end_date:
                date_filter = self.create_date_range_filter(end_date=end_date)
            else:
                return
        else:
            date_filter = None

        # Publish v1 content, and then publish v2 content
        self.add_child(v1_publish_steps.WebPublisher(repo, publish_conduit, config,
                                                     repo_content_unit_q=date_filter))
        self.add_child(V2WebPublisher(repo, publish_conduit, config,
                                      repo_content_unit_q=date_filter))

    def create_date_range_filter(self, start_date=None, end_date=None):
        """
        Create a date filter based on start and end dates

        :param start_date: start time for the filter
        :type  start_date: datetime.datetime
        :param end_date: end time for the filter
        :type  end_date: datetime.datetime

        :return: Q object with start and/or end dates, or None if start and end dates are not
                 provided
        :rtype:  mongoengine.Q or types.NoneType
        """
        if start_date:
            start_date = dateutils.format_iso8601_datetime(start_date)
        if end_date:
            end_date = dateutils.format_iso8601_datetime(end_date)

        if start_date and end_date:
            return mongoengine.Q(created__gte=start_date, created__lte=end_date)
        elif start_date:
            return mongoengine.Q(created__gte=start_date)
        elif end_date:
            return mongoengine.Q(created__lte=end_date)

    def get_predistributor(self):
        """
        Returns the distributor that is configured as postdistributor.
        """
        predistributor_id = self.get_config().flatten().get("predistributor_id", None)
        if predistributor_id:
            return Distributor.objects.get_or_404(repo_id=self.repo.id,
                                                  distributor_id=predistributor_id)


class V2WebPublisher(publish_step.PublishStep):
    """
    This class performs the work of publishing a v2 Docker repository.
    """
    def __init__(self, repo, publish_conduit, config, repo_content_unit_q=None):
        """
        Initialize the V2WebPublisher.

        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        :param repo_content_unit_q: optional Q object that will be applied to the queries performed
                                    against RepoContentUnit model
        :type  repo_content_unit_q: mongoengine.Q
        """
        super(V2WebPublisher, self).__init__(
            step_type=constants.PUBLISH_STEP_WEB_PUBLISHER, repo=repo,
            publish_conduit=publish_conduit, config=config)

        self.redirect_data = {1: set(), 2: set(), 'list': set(), 'amd64': {}}

        docker_api_version = 'v2'
        publish_dir = configuration.get_web_publish_dir(repo, config, docker_api_version)
        app_file = configuration.get_redirect_file_name(repo)
        app_publish_location = os.path.join(
            configuration.get_app_publish_dir(config, docker_api_version), app_file)
        self.working_dir = os.path.join(self.get_working_dir(), docker_api_version)
        misc.mkdir(self.working_dir)
        self.web_working_dir = os.path.join(self.get_working_dir(), 'web')
        master_publish_dir = configuration.get_master_publish_dir(repo, config, docker_api_version)
        atomic_publish_step = publish_step.AtomicDirectoryPublishStep(
            self.get_working_dir(), [('', publish_dir), (app_file, app_publish_location)],
            master_publish_dir, step_type=constants.PUBLISH_STEP_OVER_HTTP)
        atomic_publish_step.description = _('Making v2 files available via web.')
        self.add_child(PublishBlobsStep(repo_content_unit_q=repo_content_unit_q))
        self.publish_manifests_step = PublishManifestsStep(
            repo_content_unit_q=repo_content_unit_q)
        self.add_child(self.publish_manifests_step)
        self.publish_manifest_lists_step = PublishManifestListsStep(
            repo_content_unit_q=repo_content_unit_q)
        self.add_child(self.publish_manifest_lists_step)
        self.add_child(PublishTagsStep())
        self.add_child(RedirectFileStep(os.path.join(self.get_working_dir(), app_file)))
        self.add_child(atomic_publish_step)


class PublishBlobsStep(publish_step.UnitModelPluginStep):
    """
    Publish Blobs.
    """

    def __init__(self, repo_content_unit_q=None):
        """
        Initialize the PublishBlobsStep, setting its description and calling the super class's
        __init__().

        param repo_content_unit_q: optional Q object that will be applied to the queries performed
                                    against RepoContentUnit model
        :type  repo_content_unit_q: mongoengine.Q
        """
        super(PublishBlobsStep, self).__init__(step_type=constants.PUBLISH_STEP_BLOBS,
                                               model_classes=[models.Blob],
                                               repo_content_unit_q=repo_content_unit_q)
        self.description = _('Publishing Blobs.')

    def process_main(self, item):
        """
        Link the item to the Blob file.

        :param item: The Blob to process
        :type  item: pulp_docker.plugins.models.Blob
        """
        misc.create_symlink(item._storage_path,
                            os.path.join(self.get_blobs_directory(), item.unit_key['digest']))

    def get_blobs_directory(self):
        """
        Get the directory where the blobs published to the web should be linked.

        :return: The path to where blobs should be published.
        :rtype:  basestring
        """
        return os.path.join(self.parent.get_working_dir(), 'blobs')


class PublishManifestsStep(publish_step.UnitModelPluginStep):
    """
    Publish Manifests.
    """

    def __init__(self, repo_content_unit_q=None):
        """
        Initialize the PublishManifestsStep, setting its description and calling the super class's
        __init__().

        :param repo_content_unit_q: optional Q object that will be applied to the queries performed
                                    against RepoContentUnit model
        :type  repo_content_unit_q: mongoengine.Q

        """
        super(PublishManifestsStep, self).__init__(step_type=constants.PUBLISH_STEP_MANIFESTS,
                                                   model_classes=[models.Manifest],
                                                   repo_content_unit_q=repo_content_unit_q)
        self.description = _('Publishing Manifests.')

    def process_main(self, item):
        """
        Link the item to the Manifest file.

        :param item: The Manifest to process
        :type  item: pulp_docker.plugins.models.Manifest
        """
        misc.create_symlink(item._storage_path,
                            os.path.join(self.get_manifests_directory(), str(item.schema_version),
                                         item.unit_key['digest']))
        self.parent.redirect_data[item.schema_version].add(item.unit_key['digest'])

    def get_manifests_directory(self):
        """
        Get the directory where the Manifests published to the web should be linked.

        :return: The path to where Manifests should be published.
        :rtype:  basestring
        """
        return os.path.join(self.parent.get_working_dir(), 'manifests')


class PublishManifestListsStep(publish_step.UnitModelPluginStep):
    """
    Publish ManifestLists.
    """

    def __init__(self, repo_content_unit_q=None):
        """
        Initialize the PublishManifestListsStep, setting its description and calling the super
        class's __init__().

        :param repo_content_unit_q: optional Q object that will be applied to the queries performed
                                    against RepoContentUnit model
        :type  repo_content_unit_q: mongoengine.Q

        """
        super(PublishManifestListsStep, self).__init__(
            step_type=constants.PUBLISH_STEP_MANIFEST_LISTS,
            model_classes=[models.ManifestList],
            repo_content_unit_q=repo_content_unit_q)
        self.description = _('Publishing Manifest Lists.')

    def process_main(self, item):
        """
        Link the item to the Manifest List file.

        :param item: The Manifest List to process
        :type  item: pulp_docker.plugins.models.ManifestList
        """
        misc.create_symlink(item._storage_path,
                            os.path.join(self.get_manifests_directory(),
                                         constants.MANIFEST_LIST_TYPE, item.unit_key['digest']))
        redirect_data = self.parent.redirect_data
        redirect_data[constants.MANIFEST_LIST_TYPE].add(item.unit_key['digest'])
        if item.amd64_digest:
            # we query the tag collection because the manifest list model does not contain
            # the tag field anymore
            # Manifest list can have several tags
            tags = models.Tag.objects.filter(manifest_digest=item.digest,
                                             repo_id=self.get_repo().id)
            for tag in tags:
                redirect_data['amd64'][tag.name] = (item.amd64_digest,
                                                    item.amd64_schema_version)

    def get_manifests_directory(self):
        """
        Get the directory where the Manifests published to the web should be linked.

        :return: The path to where Manifests should be published.
        :rtype:  basestring
        """
        return os.path.join(self.parent.get_working_dir(), 'manifests')


class PublishTagsStep(publish_step.UnitModelPluginStep):
    """
    Publish Tags.
    """

    def __init__(self):
        """
        Initialize the PublishTagsStep, setting its description and calling the super class's
        __init__().
        """
        super(PublishTagsStep, self).__init__(step_type=constants.PUBLISH_STEP_TAGS,
                                              model_classes=[models.Tag])
        self.description = _('Publishing Tags.')
        # Collect the tag names we've seen so we can write them out during the finalize() method.
        self._tag_names = set()

    def process_main(self, item):
        """
        Create the manifest tag links.

        :param item: The tag to process
        :type  item: pulp_docker.plugins.models.Tag
        """
        try:
            manifest = models.Manifest.objects.get(digest=item.manifest_digest)
            schema_version = manifest.schema_version
        except mongoengine.DoesNotExist:
            manifest = models.ManifestList.objects.get(digest=item.manifest_digest)
            schema_version = constants.MANIFEST_LIST_TYPE
        misc.create_symlink(
            manifest._storage_path,
            os.path.join(self.parent.publish_manifests_step.get_manifests_directory(),
                         str(schema_version), item.name))
        self._tag_names.add(item.name)
        self.parent.redirect_data[schema_version].add(item.name)

    def finalize(self):
        """
        Write the Tag list file so that clients can retrieve the list of available Tags.
        """
        tags_path = os.path.join(self.parent.get_working_dir(), 'tags')
        misc.mkdir(tags_path)
        with open(os.path.join(tags_path, 'list'), 'w') as list_file:
            tag_data = {
                'name': configuration.get_repo_registry_id(self.get_repo(), self.get_config()),
                'tags': list(self._tag_names)}
            list_file.write(json.dumps(tag_data))
        # We don't need the tag names anymore
        del self._tag_names


class RedirectFileStep(publish_step.PublishStep):
    """
    This step creates the JSON file that describes the published repository for Crane to use.
    """
    def __init__(self, app_publish_location):
        """
        Initialize the step.

        :param app_publish_location: The full path to the location of the JSON file that this step
                                     will generate.
        :type  app_publish_location: basestring
        """
        super(RedirectFileStep, self).__init__(step_type=constants.PUBLISH_STEP_REDIRECT_FILE)
        self.app_publish_location = app_publish_location

    def process_main(self):
        """
        Publish the JSON file for Crane.
        """
        registry = configuration.get_repo_registry_id(self.get_repo(), self.get_config())
        redirect_url = configuration.get_redirect_url(self.get_config(), self.get_repo(), 'v2')
        redirect_data = self.parent.redirect_data
        schema2_data = redirect_data[2]
        manifest_list_data = redirect_data['list']
        manifest_list_amd64 = redirect_data['amd64']

        rdata = {
            'type': 'pulp-docker-redirect', 'version': 4, 'repository': self.get_repo().id,
            'repo-registry-id': registry, 'url': redirect_url,
            'protected': self.get_config().get('protected', False),
            'schema2_data': list(schema2_data),
            'manifest_list_data': list(manifest_list_data),
            'manifest_list_amd64_tags': manifest_list_amd64}

        misc.mkdir(os.path.dirname(self.app_publish_location))
        with open(self.app_publish_location, 'w') as app_file:
            app_file.write(json.dumps(rdata))


class PublishTagsForRsyncStep(RSyncFastForwardUnitPublishStep):

    def __init__(self, step_type, repo_registry_id=None, repo_content_unit_q=None, repo=None,
                 config=None, remote_repo_path=None):
        """
        Sets the repo_registry_id and initializes a set to keep track of processed tags.

        :param step_type: The id of the step this processes
        :type step_type: str
        :param repo_registry_id: registry id configured in the postdistributor
        :type repo_registry_id: str
        :param repo_content_unit_q: optional Q object that will be applied to the queries performed
                                    against RepoContentUnit model
        :type  repo_content_unit_q: mongoengine.Q
        :param repo: The repo being worked on
        :type  repo: pulp.plugins.model.Repository
        :param config: The publish configuration
        :type  config: PluginCallConfiguration
        :param remote_repo_path: relative path on remote server where published repo should live
        :type remote_repo_path: str
        """
        super(PublishTagsForRsyncStep, self).__init__(step_type, [models.Tag],
                                                      repo_content_unit_q=repo_content_unit_q,
                                                      repo=repo, config=config,
                                                      remote_repo_path=remote_repo_path,
                                                      published_unit_path=['manifests'])
        self._tag_names = set()
        self.repo_registry_id = repo_registry_id

    def process_main(self, item=None):
        """
        Create the manifest tag relative links.

        :param item: The tag to process
        :type  item: pulp_docker.plugins.models.Tag
        """
        try:
            manifest = models.Manifest.objects.get(digest=item.manifest_digest)
            schema_version = str(manifest.schema_version)
        except mongoengine.DoesNotExist:
            manifest = models.ManifestList.objects.get(digest=item.manifest_digest)
            schema_version = constants.MANIFEST_LIST_TYPE
        filename = item.name
        symlink = self.make_link_unit(manifest, filename, self.get_working_dir(),
                                      self.remote_repo_path,
                                      self.get_config().get("remote")["root"],
                                      self.published_unit_path + [schema_version])
        self.parent.symlink_list.append(symlink)
        self._tag_names.add(item.name)

    def finalize(self):
        """
        Write the Tag list file so that clients can retrieve the list of available Tags.
        """
        tags_path = os.path.join(self.parent.get_working_dir(), '.relative', 'tags')
        misc.mkdir(tags_path)
        with open(os.path.join(tags_path, 'list'), 'w') as list_file:
            tag_data = {
                'name': self.repo_registry_id,
                'tags': list(self._tag_names)}
            list_file.write(json.dumps(tag_data))
        # We don't need the tag names anymore
        del self._tag_names


class DockerRsyncPublisher(Publisher):

    REPO_CONTENT_TYPES = (constants.IMAGE_TYPE_ID, constants.BLOB_TYPE_ID,
                          constants.MANIFEST_TYPE_ID, constants.MANIFEST_LIST_TYPE_ID)

    REPO_CONTENT_MODELS = (models.Blob, models.Manifest, models.ManifestList, models.Image)

    def _get_postdistributor(self):
        """
        Returns the distributor object representing the postdistributor. A postdistirbutor is the
        distributor used to publish the repository after an rsync publish occurs.

        :return: postdistributor that was configured in rsync distributor's config
        :rtype: pulp.server.db.model.Distributor
        :raise pulp_exceptions.MissingResource: if distributor with postdistributor_id is found for
               this repo
        """
        postdistributor_id = self.get_config().flatten().get("postdistributor_id", None)
        return Distributor.objects.get_or_404(repo_id=self.repo.id,
                                              distributor_id=postdistributor_id)

    def _add_necesary_steps(self, date_filter=None, config=None):
        """
        This method adds all the steps that are needed to accomplish an RPM rsync publish. This
        includes:

        Unit Query Step - selects units associated with the repo based on the date_filter and
                          creates relative symlinks
        Tag Generation Step  - creates relative symlinks for for all tags and writes out list file
        Rsync Step (content units) - rsyncs content units from /var/lib/pulp/content to remote
                                     server
        Rsync Step (symlinks) - rsyncs symlinks from working directory to remote server

        :param date_filter: Q object with start and/or end dates, or None if start and end dates
                             are not provided
        :type date_filter: mongoengine.Q or types.NoneType
        :param config: distributor configuration
        :type config: pulp.plugins.config.PluginCallConfiguration

        :return: None
        """
        postdistributor = self._get_postdistributor()
        repo_registry_id = configuration.get_repo_registry_id(self.repo, postdistributor.config)
        remote_repo_path = configuration.get_remote_repo_relative_path(self.repo, self.config)

        unit_models = {constants.IMAGE_TYPE_ID: models.Image,
                       constants.MANIFEST_TYPE_ID: models.Manifest,
                       constants.MANIFEST_LIST_TYPE_ID: models.ManifestList,
                       constants.BLOB_TYPE_ID: models.Blob}

        for unit_type in DockerRsyncPublisher.REPO_CONTENT_TYPES:
            gen_step = RSyncFastForwardUnitPublishStep("Unit query step (things)",
                                                       [unit_models[unit_type]],
                                                       repo=self.repo,
                                                       repo_content_unit_q=date_filter,
                                                       remote_repo_path=remote_repo_path)
            self.add_child(gen_step)

        self.add_child(PublishTagsForRsyncStep("Generate tags step",
                                               repo=self.repo,
                                               repo_content_unit_q=date_filter,
                                               remote_repo_path=remote_repo_path,
                                               repo_registry_id=repo_registry_id))

        origin_dest_prefix = self.get_units_directory_dest_path()
        origin_src_prefix = self.get_units_src_path()

        self.add_child(RSyncPublishStep("Rsync step (content units)", self.content_unit_file_list,
                                        origin_src_prefix, origin_dest_prefix,
                                        config=config))

        # Stop here if distributor is only supposed to publish actual content
        if self.get_config().flatten().get("content_units_only"):
            return

        self.add_child(RSyncPublishStep("Rsync step (symlinks)",
                                        self.symlink_list, self.symlink_src, remote_repo_path,
                                        config=config, links=True,
                                        delete=self.config.get("delete")))

        if constants.TAG_TYPE_ID in self.repo.content_unit_counts:
            self.add_child(RSyncPublishStep("Rsync step (tags list)", ["tags/list"],
                                            os.path.join(self.get_working_dir(), '.relative'),
                                            remote_repo_path, config=config, links=True))
