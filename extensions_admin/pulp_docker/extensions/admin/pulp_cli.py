from gettext import gettext as _

from pulp.client.commands.repo import cudl, sync_publish, status
from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliOption

from pulp_docker.common import constants
from pulp_docker.extensions.admin.cudl import CreateDockerRepositoryCommand
from pulp_docker.extensions.admin.cudl import UpdateDockerRepositoryCommand
from pulp_docker.extensions.admin.images import ImageCopyCommand, ImageRemoveCommand
from pulp_docker.extensions.admin.upload import UploadDockerImageCommand
from pulp_docker.extensions.admin.repo_list import ListDockerRepositoriesCommand


SECTION_ROOT = 'docker'
DESC_ROOT = _('manage docker images')

SECTION_REPO = 'repo'
DESC_REPO = _('repository lifecycle commands')

SECTION_UPLOADS = 'uploads'
DESC_UPLOADS = _('upload docker images into a repository')

SECTION_PUBLISH = 'publish'
DESC_PUBLISH = _('publish a docker repository')

SECTION_EXPORT = 'export'
DESC_EXPORT = _('export a docker repository')
DESC_EXPORT_RUN = _('triggers an immediate export of a repository to a tar file')
DESC_EXPORT_FILE = _('the full path for an export file; if specified, the repository will be '
                     'exported as a tar file to the given file on the server.  '
                     'The web server\'s user must have the permission to write the file specified.')

OPTION_EXPORT_FILE = PulpCliOption('--export-file', DESC_EXPORT_FILE, required=False)


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
    add_export_section(context, repo_section)


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
    repo_section.add_command(UpdateDockerRepositoryCommand(context))
    repo_section.add_command(ImageRemoveCommand(context))
    repo_section.add_command(ImageCopyCommand(context))
    repo_section.add_command(ListDockerRepositoriesCommand(context))

    return repo_section


def add_publish_section(context, parent_section):
    """
    add a publish section to the repo section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the repo section should be added
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


def add_export_section(context, parent_section):
    """
    add a export section to the parent section

    :type  context: pulp.client.extensions.core.ClientContext
    :param parent_section:  section of the CLI to which the export section should be added
    :type  parent_section:  pulp.client.extensions.extensions.PulpCliSection
    """
    section = parent_section.create_subsection(SECTION_EXPORT, DESC_EXPORT)
    section.add_command(
        sync_publish.RunPublishRepositoryCommand(context=context,
                                                 renderer=status.PublishStepStatusRenderer(context),
                                                 distributor_id=constants.CLI_EXPORT_DISTRIBUTOR_ID,
                                                 description=DESC_EXPORT_RUN,
                                                 override_config_options=[OPTION_EXPORT_FILE]))
    section.add_command(
        sync_publish.PublishStatusCommand(context, status.PublishStepStatusRenderer(context)))

    return section
