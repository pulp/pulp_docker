import unittest

from pulp.common.constants import REPO_NOTE_TYPE_KEY

from pulp_docker.common import constants
from pulp_docker.extensions.admin import cudl


class TestCreateCommand(unittest.TestCase):
    def test_default_notes(self):
        # make sure this value is set and is correct
        self.assertEqual(cudl.CreateDockerRepositoryCommand.default_notes.get(REPO_NOTE_TYPE_KEY),
                         constants.REPO_NOTE_DOCKER)

    def test_importer_id(self):
        # this value is required to be set, so just make sure it's correct
        self.assertEqual(cudl.CreateDockerRepositoryCommand.IMPORTER_TYPE_ID,
                         constants.IMPORTER_TYPE_ID)
