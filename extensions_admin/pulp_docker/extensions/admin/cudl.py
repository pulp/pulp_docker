from gettext import gettext as _

from okaara import parsers as okaara_parsers
from pulp.client import arg_utils
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.repo.cudl import CreateAndConfigureRepositoryCommand
from pulp.client.commands.repo.cudl import UpdateRepositoryCommand
from pulp.client.commands.repo.importer_config import ImporterConfigMixin
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.client.extensions.extensions import PulpCliOption

from pulp_docker.common import constants, tags
from pulp_docker.extensions.admin import parsers as docker_parsers


d = _('if "true", on each successful sync the repository will automatically be '
      'published; if "false" content will only be available after manually publishing '
      'the repository; defaults to "true"')
OPT_AUTO_PUBLISH = PulpCliOption('--auto-publish', d, required=False, default='true',
                                 parse_func=okaara_parsers.parse_boolean)

d = _('The URL that will be used when generating the redirect map for connecting the docker '
      'API to the location the content is stored. '
      'The value defaults to https://<server_name_from_pulp_server.conf>/pulp/docker/<repo_name>.')
OPT_REDIRECT_URL = PulpCliOption('--redirect-url', d, required=False)

d = _('the name that will be used for this repository in the Docker registry. If not specified, '
      'the repo id will be used')
OPT_REPO_REGISTRY_ID = PulpCliOption('--repo-registry-id', d, required=False)

d = _('if "true" requests for this repo will be checked for an entitlement certificate authorizing '
      'the server url for this repository; if "false" no authorization checking will be done.')
OPT_PROTECTED = PulpCliOption('--protected', d, required=False,
                              parse_func=okaara_parsers.parse_boolean)

d = _('Tag a particular image in the repository. The format of the parameter is '
      '"<tag_name>:<image_hash>"; for example: "latest:abc123"')
OPTION_TAG = PulpCliOption('--tag', d, required=False, allow_multiple=True,
                           parse_func=docker_parsers.parse_colon_separated)

d = _('Remove the specified tag from the repository. This only removes the tag; the underlying '
      'image will remain in the repository.')
OPTION_REMOVE_TAG = PulpCliOption('--remove-tag', d, required=False, allow_multiple=True)

d = _('name of the upstream repository')
OPT_UPSTREAM_NAME = PulpCliOption('--upstream-name', d, required=False)

d = _('Enable sync of v1 API. defaults to "true"')
OPT_ENABLE_V1 = PulpCliOption('--enable-v1', d, required=False,
                              parse_func=okaara_parsers.parse_boolean)

d = _('Enable sync of v2 API. defaults to "true"')
OPT_ENABLE_V2 = PulpCliOption('--enable-v2', d, required=False,
                              parse_func=okaara_parsers.parse_boolean)


DESC_FEED = _('URL for the upstream docker index, not including repo name')


class CreateDockerRepositoryCommand(CreateAndConfigureRepositoryCommand, ImporterConfigMixin):
    default_notes = {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DOCKER}
    IMPORTER_TYPE_ID = constants.IMPORTER_TYPE_ID

    def __init__(self, context):
        CreateAndConfigureRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, include_ssl=True, include_sync=True,
                                     include_unit_policy=False)
        self.add_option(OPT_AUTO_PUBLISH)
        self.add_option(OPT_REDIRECT_URL)
        self.add_option(OPT_PROTECTED)
        self.add_option(OPT_REPO_REGISTRY_ID)
        self.add_option(OPT_ENABLE_V1)
        self.add_option(OPT_ENABLE_V2)
        self.sync_group.add_option(OPT_UPSTREAM_NAME)
        self.options_bundle.opt_feed.description = DESC_FEED

    def _describe_distributors(self, user_input):
        """
        Subclasses should override this to provide whatever option parsing
        is needed to create distributor configs.

        :param user_input:  dictionary of data passed in by okaara
        :type  user_inpus:  dict

        :return:    list of dict containing distributor_type_id,
                    repo_plugin_config, auto_publish, and distributor_id (the same
                    that would be passed to the RepoDistributorAPI.create call).
        :rtype:     list of dict
        """
        config = {}
        value = user_input.pop(OPT_PROTECTED.keyword, None)
        if value is not None:
            config[constants.CONFIG_KEY_PROTECTED] = value

        value = user_input.pop(OPT_REDIRECT_URL.keyword, None)
        if value is not None:
            config[constants.CONFIG_KEY_REDIRECT_URL] = value

        value = user_input.pop(OPT_REPO_REGISTRY_ID.keyword, None)
        if value is not None:
            config[constants.CONFIG_KEY_REPO_REGISTRY_ID] = value

        auto_publish = user_input.get(OPT_AUTO_PUBLISH.keyword, True)
        data = [
            dict(distributor_type_id=constants.DISTRIBUTOR_WEB_TYPE_ID,
                 distributor_config=config,
                 auto_publish=auto_publish,
                 distributor_id=constants.CLI_WEB_DISTRIBUTOR_ID),
            dict(distributor_type_id=constants.DISTRIBUTOR_EXPORT_TYPE_ID,
                 distributor_config=config,
                 auto_publish=False, distributor_id=constants.CLI_EXPORT_DISTRIBUTOR_ID)
        ]

        return data

    def _parse_importer_config(self, user_input):
        """
        Subclasses should override this to provide whatever option parsing
        is needed to create an importer config.

        :param user_input:  dictionary of data passed in by okaara
        :type  user_input:  dict

        :return:    importer config
        :rtype:     dict
        """
        config = self.parse_user_input(user_input)

        name = user_input.pop(OPT_UPSTREAM_NAME.keyword)
        if name is not None:
            config[constants.CONFIG_KEY_UPSTREAM_NAME] = name
        enable_v1 = user_input.pop(OPT_ENABLE_V1.keyword, None)
        if enable_v1 is not None:
            config[constants.CONFIG_KEY_ENABLE_V1] = enable_v1
        enable_v2 = user_input.pop(OPT_ENABLE_V2.keyword, None)
        if enable_v2 is not None:
            config[constants.CONFIG_KEY_ENABLE_V2] = enable_v2

        return config


class UpdateDockerRepositoryCommand(UpdateRepositoryCommand, ImporterConfigMixin):

    def __init__(self, context):
        UpdateRepositoryCommand.__init__(self, context)
        ImporterConfigMixin.__init__(self, include_ssl=True, include_sync=True,
                                     include_unit_policy=False)
        self.add_option(OPTION_TAG)
        self.add_option(OPTION_REMOVE_TAG)
        self.add_option(OPT_AUTO_PUBLISH)
        self.add_option(OPT_REDIRECT_URL)
        self.add_option(OPT_PROTECTED)
        self.add_option(OPT_REPO_REGISTRY_ID)
        self.add_option(OPT_ENABLE_V1)
        self.sync_group.add_option(OPT_UPSTREAM_NAME)
        self.options_bundle.opt_feed.description = DESC_FEED

    def run(self, **kwargs):
        arg_utils.convert_removed_options(kwargs)

        importer_config = self.parse_user_input(kwargs)

        name = kwargs.pop(OPT_UPSTREAM_NAME.keyword, None)
        if name is not None:
            importer_config[constants.CONFIG_KEY_UPSTREAM_NAME] = name

        if importer_config:
            kwargs['importer_config'] = importer_config

        # Update distributor configuration
        web_config = {}
        export_config = {}
        value = kwargs.pop(OPT_PROTECTED.keyword, None)
        if value is not None:
            web_config[constants.CONFIG_KEY_PROTECTED] = value
            export_config[constants.CONFIG_KEY_PROTECTED] = value

        value = kwargs.pop(OPT_REDIRECT_URL.keyword, None)
        if value is not None:
            web_config[constants.CONFIG_KEY_REDIRECT_URL] = value
            export_config[constants.CONFIG_KEY_REDIRECT_URL] = value

        value = kwargs.pop(OPT_REPO_REGISTRY_ID.keyword, None)
        if value is not None:
            web_config[constants.CONFIG_KEY_REPO_REGISTRY_ID] = value
            export_config[constants.CONFIG_KEY_REPO_REGISTRY_ID] = value

        value = kwargs.pop(OPT_AUTO_PUBLISH.keyword, None)
        if value is not None:
            web_config['auto_publish'] = value

        if web_config or export_config:
            kwargs['distributor_configs'] = {}

        if web_config:
            kwargs['distributor_configs'][constants.CLI_WEB_DISTRIBUTOR_ID] = web_config

        if export_config:
            kwargs['distributor_configs'][constants.CLI_EXPORT_DISTRIBUTOR_ID] = export_config

        # Update Tags
        repo_id = kwargs.get(OPTION_REPO_ID.keyword)
        response = self.context.server.repo.repository(repo_id).response_body
        scratchpad = response.get(u'scratchpad', {})
        image_tags = scratchpad.get(u'tags', [])

        user_tags = kwargs.get(OPTION_TAG.keyword)
        if user_tags:
            user_tags = kwargs.pop(OPTION_TAG.keyword)
            for tag, image_id in user_tags:
                if len(image_id) < 6:
                    msg = _('The image id, (%s), must be at least 6 characters.')
                    self.prompt.render_failure_message(msg % image_id)
                    return

            # Ensure the specified images exist in the repo
            images_requested = set([image_id for tag, image_id in user_tags])
            images = ['^%s' % image_id for image_id in images_requested]
            image_regex = '|'.join(images)
            search_criteria = {
                'type_ids': constants.IMAGE_TYPE_ID,
                'match': [['image_id', image_regex]],
                'fields': ['image_id']
            }

            response = self.context.server.repo_unit.search(repo_id, **search_criteria).\
                response_body
            if len(response) != len(images):
                images_found = set([x[u'metadata'][u'image_id'] for x in response])
                missing_images = images_requested.difference(images_found)
                msg = _('Unable to create tag in repository. The following image(s) do not '
                        'exist in the repository: %s.')
                self.prompt.render_failure_message(msg % ', '.join(missing_images))
                return

            # Get the full image id from the returned values and save in tags_to_update dictionary
            tags_to_update = {}
            for image in response:
                found_image_id = image[u'metadata'][u'image_id']
                for tag, image_id in user_tags:
                    if found_image_id.startswith(image_id):
                        tags_to_update[tag] = found_image_id

            # Create a list of tag dictionaries that can be saved on the repo scratchpad
            # using the original tags and new tags specified by the user
            image_tags = tags.generate_updated_tags(scratchpad, tags_to_update)
            scratchpad[u'tags'] = image_tags
            kwargs[u'scratchpad'] = scratchpad

        remove_tags = kwargs.get(OPTION_REMOVE_TAG.keyword)
        if remove_tags:
            kwargs.pop(OPTION_REMOVE_TAG.keyword)
            for tag in remove_tags:
                # For each tag in remove_tags, remove the respective tag dictionary
                # for matching tag.
                for image_tag in image_tags[:]:
                    if tag == image_tag[constants.IMAGE_TAG_KEY]:
                        image_tags.remove(image_tag)

            scratchpad[u'tags'] = image_tags
            kwargs[u'scratchpad'] = scratchpad

        super(UpdateDockerRepositoryCommand, self).run(**kwargs)
