import unittest

from mock import Mock
from pulp.common import constants as pulp_constants

from pulp_docker.common import constants
from pulp_docker.extensions.admin.repo_list import ListDockerRepositoriesCommand


class TestListDockerRepositoriesCommand(unittest.TestCase):
    def setUp(self):
        self.context = Mock()
        self.context.config = {'output': {'poll_frequency_in_seconds': 3}}

    def test_get_all_repos(self):
        self.context.server.repo.repositories.return_value.response_body = 'foo'
        command = ListDockerRepositoriesCommand(self.context)
        result = command._all_repos({'bar': 'baz'})
        self.context.server.repo.repositories.assert_called_once_with({'bar': 'baz'})
        self.assertEquals('foo', result)

    def test_get_all_repos_caches_results(self):
        command = ListDockerRepositoriesCommand(self.context)
        command.all_repos_cache = 'foo'
        result = command._all_repos({'bar': 'baz'})
        self.assertFalse(self.context.server.repo.repositories.called)
        self.assertEquals('foo', result)

    def test_get_repositories(self):
        # Setup
        repos = [
            {
                'id': 'matching',
                'notes': {pulp_constants.REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DOCKER, },
                'importers': [
                    {'config': {}}
                ],
                'distributors': [
                    {'id': constants.CLI_EXPORT_DISTRIBUTOR_ID},
                    {'id': constants.CLI_WEB_DISTRIBUTOR_ID}
                ]
            },
            {'id': 'non-rpm-repo',
             'notes': {}}
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = ListDockerRepositoriesCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'matching')

        #   Make sure the export distributor was removed
        self.assertEqual(len(repos[0]['distributors']), 1)
        self.assertEqual(repos[0]['distributors'][0]['id'], constants.CLI_EXPORT_DISTRIBUTOR_ID)

    def test_get_repositories_no_details(self):
        # Setup
        repos = [
            {
                'id': 'foo',
                'display_name': 'bar',
                'notes': {pulp_constants.REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DOCKER, }
            }
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = ListDockerRepositoriesCommand(self.context)
        repos = command.get_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['id'], 'foo')
        self.assertTrue('importers' not in repos[0])
        self.assertTrue('distributors' not in repos[0])

    def test_get_other_repositories(self):
        # Setup
        repos = [
            {
                'repo_id': 'matching',
                'notes': {pulp_constants.REPO_NOTE_TYPE_KEY: constants.REPO_NOTE_DOCKER, },
                'distributors': [
                    {'id': constants.CLI_EXPORT_DISTRIBUTOR_ID},
                    {'id': constants.CLI_WEB_DISTRIBUTOR_ID}
                ]
            },
            {
                'repo_id': 'non-rpm-repo-1',
                'notes': {}
            }
        ]
        self.context.server.repo.repositories.return_value.response_body = repos

        # Test
        command = ListDockerRepositoriesCommand(self.context)
        repos = command.get_other_repositories({})

        # Verify
        self.assertEqual(1, len(repos))
        self.assertEqual(repos[0]['repo_id'], 'non-rpm-repo-1')
