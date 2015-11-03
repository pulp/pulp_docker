import unittest

import mock
from pulp.client.commands.repo.cudl import CreateRepositoryCommand, DeleteRepositoryCommand
from pulp.client.commands.repo.cudl import UpdateRepositoryCommand
from pulp.client.commands.repo.sync_publish import PublishStatusCommand,\
    RunPublishRepositoryCommand, RunSyncRepositoryCommand
from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.core import PulpCli
from pulp.client.extensions.extensions import PulpCliSection

from pulp_docker.extensions.admin import pulp_cli
from pulp_docker.extensions.admin import images
from pulp_docker.extensions.admin import manifest
from pulp_docker.extensions.admin.repo_list import ListDockerRepositoriesCommand


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

        # verify that sections exist and have the right commands and subsections
        docker_section = context.cli.root_section.subsections['docker']

        repo_section = docker_section.subsections['repo']
        self.assertTrue(isinstance(repo_section.commands['create'], CreateRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['delete'], DeleteRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['update'], UpdateRepositoryCommand))
        self.assertTrue(isinstance(repo_section.commands['list'], ListDockerRepositoriesCommand))
        self.assertTrue(isinstance(repo_section.subsections['search'], PulpCliSection))
        self.assertTrue(isinstance(repo_section.subsections['copy'], PulpCliSection))
        self.assertTrue(isinstance(repo_section.subsections['remove'], PulpCliSection))

        upload_section = repo_section.subsections['uploads']
        self.assertTrue(isinstance(upload_section.commands['upload'], UploadCommand))

        section = repo_section.subsections['sync']
        self.assertTrue(isinstance(section.commands['run'], RunSyncRepositoryCommand))

        section = repo_section.subsections['publish']
        self.assertTrue(isinstance(section.commands['status'], PublishStatusCommand))
        self.assertTrue(isinstance(section.commands['run'], RunPublishRepositoryCommand))

        section = repo_section.subsections['export']
        self.assertTrue(isinstance(section.commands['status'], PublishStatusCommand))
        self.assertTrue(isinstance(section.commands['run'], RunPublishRepositoryCommand))

        section = repo_section.subsections['search']
        self.assertTrue(isinstance(section.commands['image'], images.ImageSearchCommand))
        self.assertTrue(isinstance(section.commands['manifest'], manifest.ManifestSearchCommand))

        section = repo_section.subsections['copy']
        self.assertTrue(isinstance(section.commands['image'], images.ImageCopyCommand))
        self.assertTrue(isinstance(section.commands['manifest'], manifest.ManifestCopyCommand))

        section = repo_section.subsections['remove']
        self.assertTrue(isinstance(section.commands['image'], images.ImageRemoveCommand))
        self.assertTrue(isinstance(section.commands['manifest'], manifest.ManifestRemoveCommand))
