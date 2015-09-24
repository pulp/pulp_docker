from gettext import gettext as _
import json
import os

from pulp.plugins.util import misc, publish_step

from pulp_docker.common import constants, models
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
        super(WebPublisher, self).__init__(constants.PUBLISH_STEP_WEB_PUBLISHER,
                                           repo, publish_conduit, config)

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
        super(V2WebPublisher, self).__init__(constants.PUBLISH_STEP_WEB_PUBLISHER,
                                             repo, publish_conduit, config)

        # Map tags we've seen to the "newest" manifests that go with them
        self.tags = {}
        docker_api_version = 'v2'
        publish_dir = configuration.get_web_publish_dir(repo, config, docker_api_version)
        app_file = configuration.get_redirect_file_name(repo)
        app_publish_location = os.path.join(
            configuration.get_app_publish_dir(config, docker_api_version), app_file)
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


class PublishBlobsStep(publish_step.UnitPublishStep):
    """
    Publish Blobs.
    """

    def __init__(self):
        """
        Initialize the PublishBlobsStep, setting its description and calling the super class's
        __init__().
        """
        super(PublishBlobsStep, self).__init__(constants.PUBLISH_STEP_BLOBS,
                                               models.Blob.TYPE_ID)
        self.description = _('Publishing Blobs.')

    def process_unit(self, unit):
        """
        Link the unit to the Blob file.

        :param unit: The unit to process
        :type unit:  pulp_docker.common.models.Blob
        """
        self._create_symlink(unit.storage_path,
                             os.path.join(self.get_blobs_directory(), unit.unit_key['digest']))

    def get_blobs_directory(self):
        """
        Get the directory where the blobs published to the web should be linked.

        :return: The path to where blobs should be published.
        :rtype:  basestring
        """
        return os.path.join(self.get_working_dir(), 'blobs')


class PublishManifestsStep(publish_step.UnitPublishStep):
    """
    Publish Manifests.
    """

    def __init__(self):
        """
        Initialize the PublishManifestsStep, setting its description and calling the super class's
        __init__().
        """
        super(PublishManifestsStep, self).__init__(constants.PUBLISH_STEP_MANIFESTS,
                                                   models.Manifest.TYPE_ID)
        self.description = _('Publishing Manifests.')

    def process_unit(self, unit):
        """
        Link the unit to the Manifest file.

        :param unit: The unit to process
        :type unit:  pulp_docker.common.models.Blob
        """
        # Keep track of the "latest" Manifest we've seen by looking for the one with the newest id
        if 'latest' not in self.parent.tags or unit._id > self.parent.tags['latest']._id:
            self.parent.tags['latest'] = unit
        # Keep track of the newest Manifest we've seen with this tag by looking for the one with the
        # newest id
        if unit.metadata['tag'] not in self.parent.tags or \
                unit.id > self.parent.tags[unit.metadata['tag']]:
            self.parent.tags[unit.metadata['tag']] = unit

        self._create_symlink(unit.storage_path,
                             os.path.join(self.get_manifests_directory(), unit.unit_key['digest']))

    def get_manifests_directory(self):
        """
        Get the directory where the Manifests published to the web should be linked.

        :return: The path to where Manifests should be published.
        :rtype:  basestring
        """
        return os.path.join(self.get_working_dir(), 'manifests')


class PublishTagsStep(publish_step.PublishStep):
    """
    Publish Tags.
    """

    def __init__(self):
        """
        Initialize the PublishTagsStep, setting its description and calling the super class's
        __init__().
        """
        super(PublishTagsStep, self).__init__(constants.PUBLISH_STEP_TAGS)
        self.description = _('Publishing Tags.')

    def process_main(self):
        """
        Create the list file and add the manifest tag links.

        :param unit: The unit to process
        :type unit:  pulp_docker.common.models.Tag
        """
        tags_path = os.path.join(self.get_working_dir(), 'tags')
        misc.mkdir(tags_path)
        with open(os.path.join(tags_path, 'list'), 'w') as list_file:
            list_file.write(json.dumps(list(self.parent.tags)))

        # Add the links to make Manifests accessible by tags as well
        for tag, unit in self.parent.tags.items():
            self.parent.publish_manifests_step._create_symlink(
                unit.storage_path,
                os.path.join(self.parent.publish_manifests_step.get_manifests_directory(), tag))


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
        super(RedirectFileStep, self).__init__(constants.PUBLISH_STEP_REDIRECT_FILE)
        self.app_publish_location = app_publish_location

    def process_main(self):
        """
        Publish the JSON file for Crane.
        """
        registry = configuration.get_repo_registry_id(self.get_repo(), self.get_config())
        redirect_url = configuration.get_redirect_url(self.get_config(), self.get_repo())

        redirect_data = {
            'type': 'pulp-docker-redirect', 'version': 2, 'repository': self.get_repo().id,
            'repo-registry-id': registry, 'url': redirect_url,
            'protected': self.get_config().get('protected', False)}

        misc.mkdir(os.path.dirname(self.app_publish_location))
        with open(self.app_publish_location, 'w') as app_file:
            app_file.write(json.dumps(redirect_data))
