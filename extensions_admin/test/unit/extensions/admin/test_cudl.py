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
        user_input = {'redirect-url': 'foo',
                      'protected': False}
        result = command._describe_distributors(user_input)
        target_result = {
            "distributor_type": constants.DISTRIBUTOR_WEB_TYPE_ID,
            "distributor_config": {'redirect-url': 'foo', 'protected': False},
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


class TestUpdateDockerRepositoryCommand(unittest.TestCase):

    def setUp(self):
        self.context = Mock()
        self.command = cudl.UpdateDockerRepositoryCommand(self.context)
        self.mock_repo_response = Mock(response_body={})
        self.context.server.repo.repository.return_value = self.mock_repo_response
        self.unit_search_command = Mock(response_body=[{u'metadata': {u'image_id': 'bar'}}])
        self.context.server.repo_unit.search.return_value = self.unit_search_command

    def test_tag(self):
        user_input = {
            'repo-id': 'foo-repo',
            'tag': [['foo', 'bar123']]
        }
        self.command.run(**user_input)

        target_kwargs = {
            u'scratchpad': {u'tags': {'foo': 'bar123'}}
        }
        self.context.server.repo.update.assert_called_once_with('foo-repo', target_kwargs)

    def test_tag_partial_match_image_id_too_short(self):
        user_input = {
            'repo-id': 'foo-repo',
            'tag': [['foo', 'baz']]
        }
        self.unit_search_command.response_body = [{u'metadata': {u'image_id': 'baz123qux'}}]
        self.command.run(**user_input)
        self.assertFalse(self.context.server.repo.update.called)

    def test_tag_partial_match_image_id(self):
        user_input = {
            'repo-id': 'foo-repo',
            'tag': [['foo', 'baz123']]
        }
        self.unit_search_command.response_body = [{u'metadata': {u'image_id': 'baz123qux'}}]
        self.command.run(**user_input)

        target_kwargs = {
            u'scratchpad': {u'tags': {'foo': 'baz123qux'}}
        }
        self.context.server.repo.update.assert_called_once_with('foo-repo', target_kwargs)

    def test_multi_tag(self):
        user_input = {
            'repo-id': 'foo-repo',
            'tag': [['foo', 'bar123'], ['baz', 'bar123']]
        }
        self.command.run(**user_input)

        target_kwargs = {
            u'scratchpad': {u'tags': {'foo': 'bar123', 'baz': 'bar123'}}
        }
        self.context.server.repo.update.assert_called_once_with('foo-repo', target_kwargs)

    def test_image_not_found(self):
        user_input = {
            'repo-id': 'foo-repo',
            'tag': [['foo', 'bar123']]
        }
        self.unit_search_command.response_body = []
        self.command.run(**user_input)
        self.assertTrue(self.command.prompt.render_failure_message.called)

    def test_remove_tag(self):
        self.mock_repo_response.response_body = \
            {u'scratchpad': {u'tags': {'foo': 'bar123', 'baz': 'bar123'}}}
        user_input = {
            'repo-id': 'foo-repo',
            'remove-tag': ['foo']
        }
        self.command.run(**user_input)

        target_kwargs = {
            u'scratchpad': {u'tags': {'baz': 'bar123'}}
        }
        self.context.server.repo.update.assert_called_once_with('foo-repo', target_kwargs)
