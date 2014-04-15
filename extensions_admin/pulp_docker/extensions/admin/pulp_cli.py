from gettext import gettext as _

from pulp.client.commands.repo import cudl, sync_publish, status
from pulp.client.extensions.decorator import priority

from pulp_docker.common import constants
from pulp_docker.extensions.admin.cudl import CreateDockerRepositoryCommand
from pulp_docker.extensions.admin.upload import UploadDockerImageCommand


SECTION_ROOT = 'docker'
DESC_ROOT = _('manage docker images')

SECTION_REPO = 'repo'
DESC_REPO = _('repository lifecycle commands')

SECTION_UPLOADS = 'uploads'
DESC_UPLOADS = _('upload docker images into a repository')

SECTION_PUBLISH = 'publish'
DESC_PUBLISH = _('publish a docker repository')


@priority()
def initialize(context):
    """
    create the docker CLI section and add it to the root

    :type  context: pulp.client.extensions.core.ClientContext
    """
    root_section = context.cli.create_section(SECTION_ROOT, DESC_ROOT)
    repo_section = add_repo_section(context, root_section)
    add_upload_section(context, repo_section)
    add_publish_section(context, repo_section)


def add_upload_section(context, parent_section):
    """
    add an upload section to the docker section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the upload section
                            should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    upload_section = parent_section.create_subsection(SECTION_UPLOADS, DESC_UPLOADS)

    upload_section.add_command(UploadDockerImageCommand(context))

    return upload_section


def add_repo_section(context, parent_section):
    """
    add a repo section to the docker section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the repo section
                            should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    repo_section = parent_section.create_subsection(SECTION_REPO, DESC_REPO)

    repo_section.add_command(CreateDockerRepositoryCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))

    return repo_section


def add_publish_section(context, parent_section):
    """
    add a publish section to the repo section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the repo section
                            should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    section = parent_section.create_subsection(SECTION_PUBLISH, DESC_PUBLISH)

    renderer = status.PublishStepStatusRenderer(context)
    section.add_command(
        sync_publish.RunPublishRepositoryCommand(context,
                                                 renderer,
                                                 constants.CLI_WEB_DISTRIBUTOR_ID))
    section.add_command(
        sync_publish.PublishStatusCommand(context, renderer))

    return section
