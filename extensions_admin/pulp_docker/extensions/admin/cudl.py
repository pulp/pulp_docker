from gettext import gettext as _


from pulp.client import parsers
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.repo.cudl import CreateAndConfigureRepositoryCommand
from pulp.client.commands.repo.cudl import UpdateRepositoryCommand
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.client.extensions.extensions import PulpCliOption

from pulp_docker.common import constants
from pulp_docker.extensions.admin import parsers as docker_parsers


d = _('if "true", on each successful sync the repository will automatically be '
      'published; if "false" content will only be available after manually publishing '
      'the repository; defaults to "true"')
OPT_AUTO_PUBLISH = PulpCliOption('--auto-publish', d, required=False,
                                 parse_func=parsers.parse_boolean)

d = _('The URL that will be used when generating the redirect map for connecting the docker '
      'API to the location the content is stored. '
      'The value defaults to https://<server_name_from_pulp_server.conf>/pulp/docker/<repo_name>.')
OPT_REDIRECT_URL = PulpCliOption('--redirect-url', d, required=False)

d = _('if "true" requests for this repo will be checked for an entitlement certificate authorizing '
      'the server url for this repository; if "false" no authorization checking will be done.')
OPT_PROTECTED = PulpCliOption('--protected', d, required=False, parse_func=parsers.parse_boolean)

d = _('Tag a particular image in the repository. The format of the parameter is '
      '"<tag_name>:<image_hash>"; for example: "latest:abc123"')
OPTION_TAG = PulpCliOption('--tag', d, required=False, allow_multiple=True,
                           parse_func=docker_parsers.parse_colon_separated)

d = _('Remove the specified tag from the repository. This only removes the tag; the underlying '
      'image will remain in the repository.')
OPTION_REMOVE_TAG = PulpCliOption('--remove-tag', d, required=False, allow_multiple=True)


class CreateDockerRepositoryCommand(CreateAndConfigureRepositoryCommand):
    default_notes = {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DOCKER}
    IMPORTER_TYPE_ID = constants.IMPORTER_TYPE_ID

    def __init__(self, context):
        super(CreateDockerRepositoryCommand, self).__init__(context)
        self.add_option(OPT_AUTO_PUBLISH)
        self.add_option(OPT_REDIRECT_URL)
        self.add_option(OPT_PROTECTED)

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
        value = user_input.get(OPT_PROTECTED.keyword)
        if value is not None:
            config[constants.CONFIG_KEY_PROTECTED] = value

        value = user_input.get(OPT_REDIRECT_URL.keyword)
        if value is not None:
            config[constants.CONFIG_KEY_REDIRECT_URL] = value

        auto_publish = user_input.get('auto-publish', True)
        data = [
            dict(distributor_type=constants.DISTRIBUTOR_WEB_TYPE_ID,
                 distributor_config=config,
                 auto_publish=auto_publish,
                 distributor_id=constants.CLI_WEB_DISTRIBUTOR_ID),
            dict(distributor_type=constants.DISTRIBUTOR_EXPORT_TYPE_ID,
                 distributor_config=config,
                 auto_publish=False, distributor_id=constants.CLI_EXPORT_DISTRIBUTOR_ID)
        ]

        return data


class UpdateDockerRepositoryCommand(UpdateRepositoryCommand):

    def __init__(self, context):
        super(UpdateDockerRepositoryCommand, self).__init__(context)
        self.add_option(OPTION_TAG)
        self.add_option(OPTION_REMOVE_TAG)

    def run(self, **kwargs):
        repo_id = kwargs.get(OPTION_REPO_ID.keyword)
        response = self.context.server.repo.repository(repo_id).response_body
        scratchpad = response.get(u'scratchpad', {})
        image_tags = scratchpad.get(u'tags', {})

        tags = kwargs.get(OPTION_TAG.keyword)
        if tags:
            tags = kwargs.pop(OPTION_TAG.keyword)
            for tag, image_id in tags:
                if len(image_id) < 6:
                    msg = _('The image id, (%s), must be at least 6 characters.')
                    self.prompt.render_failure_message(msg % image_id)
                    return

                image_tags[tag] = image_id
            # Ensure the specified images exist in the repo
            images_requested = set([image_id for tag, image_id in tags])
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

            # Get the full image id from the returned values
            for image in response:
                found_image_id = image[u'metadata'][u'image_id']
                for key, value in image_tags.iteritems():
                    if found_image_id.startswith(value):
                        image_tags[key] = found_image_id

            scratchpad[u'tags'] = image_tags
            kwargs[u'scratchpad'] = scratchpad

        remove_tags = kwargs.get(OPTION_REMOVE_TAG.keyword)
        if remove_tags:
            kwargs.pop(OPTION_REMOVE_TAG.keyword)
            for tag in remove_tags:
                image_tags.pop(tag)
            scratchpad[u'tags'] = image_tags
            kwargs[u'scratchpad'] = scratchpad

        super(UpdateDockerRepositoryCommand, self).run(**kwargs)
