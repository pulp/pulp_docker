import unittest

import mock
from pulp.client.commands.repo.cudl import CreateRepositoryCommand, DeleteRepositoryCommand
from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.core import PulpCli

from pulp_docker.extensions.admin import pulp_cli


class TestInitialize(unittest.TestCase):
    def test_structure(self):
        context = mock.MagicMock()
        context.config = {
            'filesystem': {'upload_working_dir': '/a/b/c'},
            'output': {'poll_frequency_in_seconds': 3}
        }
        context.cli = PulpCli(context)

        # create the tree of commands and sections
        pulp_cli.initialize(context)

        # verify that sections exist and have the right commands
        docker_section = context.cli.root_section.subsections['docker']

        repo_section = docker_section.subsections['repo']
        self.assertTrue(isinstance(repo_section.commands['create'], CreateRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['delete'], DeleteRepositoryCommand))

        upload_section = repo_section.subsections['uploads']
        self.assertTrue(isinstance(upload_section.commands['upload'], UploadCommand))
