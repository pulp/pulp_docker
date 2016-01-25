from gettext import gettext as _
import json
import os

from pulp.plugins.util import misc, publish_step

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

        # Publish v1 content, and then publish v2 content
        self.add_child(v1_publish_steps.WebPublisher(repo, publish_conduit, config))
        self.add_child(V2WebPublisher(repo, publish_conduit, config))


class V2WebPublisher(publish_step.PublishStep):
    """
    This class performs the work of publishing a v2 Docker repository.
    """
    def __init__(self, repo, publish_conduit, config):
        """
        Initialize the V2WebPublisher.

        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        super(V2WebPublisher, self).__init__(
            step_type=constants.PUBLISH_STEP_WEB_PUBLISHER, repo=repo,
            publish_conduit=publish_conduit, config=config)

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
        self.add_child(PublishBlobsStep())
        self.publish_manifests_step = PublishManifestsStep()
        self.add_child(self.publish_manifests_step)
        self.add_child(PublishTagsStep())
        self.add_child(atomic_publish_step)
        self.add_child(RedirectFileStep(app_publish_location))


class PublishBlobsStep(publish_step.UnitModelPluginStep):
    """
    Publish Blobs.
    """

    def __init__(self):
        """
        Initialize the PublishBlobsStep, setting its description and calling the super class's
        __init__().
        """
        super(PublishBlobsStep, self).__init__(step_type=constants.PUBLISH_STEP_BLOBS,
                                               model_classes=[models.Blob])
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

    def __init__(self):
        """
        Initialize the PublishManifestsStep, setting its description and calling the super class's
        __init__().
        """
        super(PublishManifestsStep, self).__init__(step_type=constants.PUBLISH_STEP_MANIFESTS,
                                                   model_classes=[models.Manifest])
        self.description = _('Publishing Manifests.')

    def process_main(self, item):
        """
        Link the item to the Manifest file.

        :param item: The Blob to process
        :type  item: pulp_docker.plugins.models.Blob
        """
        misc.create_symlink(item._storage_path,
                            os.path.join(self.get_manifests_directory(), item.unit_key['digest']))

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
        manifest = models.Manifest.objects.get(digest=item.manifest_digest)
        misc.create_symlink(
            manifest._storage_path,
            os.path.join(self.parent.publish_manifests_step.get_manifests_directory(), item.name))
        self._tag_names.add(item.name)

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

        redirect_data = {
            'type': 'pulp-docker-redirect', 'version': 2, 'repository': self.get_repo().id,
            'repo-registry-id': registry, 'url': redirect_url,
            'protected': self.get_config().get('protected', False)}

        misc.mkdir(os.path.dirname(self.app_publish_location))
        with open(self.app_publish_location, 'w') as app_file:
            app_file.write(json.dumps(redirect_data))
