import unittest

from mock import Mock
from pulp.common.constants import REPO_NOTE_TYPE_KEY
from pulp.devel.unit.util import compare_dict

from pulp_docker.common import constants
from pulp_docker.extensions.admin import cudl


class TestCreateDockerRepositoryCommand(unittest.TestCase):
    def test_default_notes(self):
        # make sure this value is set and is correct
        self.assertEqual(cudl.CreateDockerRepositoryCommand.default_notes.get(REPO_NOTE_TYPE_KEY),
                         constants.REPO_NOTE_DOCKER)

    def test_importer_id(self):
        # this value is required to be set, so just make sure it's correct
        self.assertEqual(cudl.CreateDockerRepositoryCommand.IMPORTER_TYPE_ID,
                         constants.IMPORTER_TYPE_ID)

    def test_describe_distributors(self):
        command = cudl.CreateDockerRepositoryCommand(Mock())
        user_input = {'server-url': 'foo',
                      'protected': False}
        result = command._describe_distributors(user_input)
        target_result = {
            "distributor_type": constants.DISTRIBUTOR_TYPE_ID,
            "distributor_config": {'server-url': 'foo', 'protected': False},
            "auto_publish": True,
            "distributor_id": constants.CLI_WEB_DISTRIBUTOR_ID
        }
        compare_dict(result[0], target_result)

    def test_describe_distributors_override_auto_publish(self):
        command = cudl.CreateDockerRepositoryCommand(Mock())
        user_input = {
            'auto-publish': False
        }
        result = command._describe_distributors(user_input)
        self.assertEquals(result[0]["auto_publish"], False)
