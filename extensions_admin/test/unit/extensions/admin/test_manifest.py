
from unittest import TestCase

from mock import patch, Mock

from pulp_docker.common.models import Manifest, Blob
from pulp_docker.extensions.admin.manifest import (
    get_formatter_for_type, options, ManifestSearchCommand,
    ManifestCopyCommand, ManifestRemoveCommand)


MODULE = 'pulp_docker.extensions.admin.manifest'


class TestGetFormatterForType(TestCase):

    def test_call_with_manifest(self):
        digest = '1234'
        formatter = get_formatter_for_type(Manifest.TYPE_ID)
        unit = dict(digest=digest)
        self.assertEqual(formatter(unit), digest)

    def test_call_with_blob(self):
        digest = '1234'
        formatter = get_formatter_for_type(Blob.TYPE_ID)
        unit = dict(digest=digest)
        self.assertEqual(formatter(unit), digest)

    def test_call_invalid_type_id(self):
        self.assertRaises(ValueError, get_formatter_for_type, '')


class TestManifestSearchCommand(TestCase):

    def test_init(self):
        context = Mock()
        command = ManifestSearchCommand(context)
        self.assertEqual(command.context, context)
        self.assertEqual(command.name, 'search')
        self.assertEqual(command.prompt, context.prompt)
        self.assertFalse(command.description is None)
        self.assertEqual(command.method, command.run)

    def test_run(self):
        repo_id = '1234'
        context = Mock()
        kwargs = {
            options.OPTION_REPO_ID.keyword: repo_id
        }
        command = ManifestSearchCommand(context)

        # test
        command.run(**kwargs)

        # validation
        context.server.repo_unit.search.assert_called_once_with(
            repo_id, type_ids=[Manifest.TYPE_ID])
        context.prompt.render_document_list(
            context.server.repo_unit.search.return_value.response_body)


class TestManifestCopyCommand(TestCase):

    def test_init(self):
        context = Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = ManifestCopyCommand(context)
        self.assertEqual(command.name, 'copy')
        self.assertFalse(command.description is None)
        self.assertEqual(command.context, context)
        self.assertEqual(command.method, command.run)

    @patch(MODULE + '.get_formatter_for_type')
    def test_get_formatter_for_type(self, get_formatter):
        context = Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = ManifestCopyCommand(context)
        formatter = command.get_formatter_for_type(Manifest.TYPE_ID)
        self.assertEqual(formatter, get_formatter.return_value)


class TestManifestRemoveCommand(TestCase):

    def test_init(self):
        context = Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = ManifestRemoveCommand(context)
        self.assertEqual(command.name, 'remove')
        self.assertFalse(command.description is None)
        self.assertEqual(command.context, context)
        self.assertEqual(command.method, command.run)

    @patch(MODULE + '.get_formatter_for_type')
    def test_get_formatter_for_type(self, get_formatter):
        context = Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = ManifestRemoveCommand(context)
        formatter = command.get_formatter_for_type(Manifest.TYPE_ID)
        self.assertEqual(formatter, get_formatter.return_value)
