from pulp.client.commands.repo.cudl import CreateAndConfigureRepositoryCommand
from pulp.common.constants import REPO_NOTE_TYPE_KEY

from pulp_docker.common import constants


class CreateDockerRepositoryCommand(CreateAndConfigureRepositoryCommand):
    default_notes = {REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DOCKER}
    IMPORTER_TYPE_ID = constants.IMPORTER_TYPE_ID
