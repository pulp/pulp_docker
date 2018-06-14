import copy
import unittest

import mock

from pulp_docker.common import constants
from pulp_docker.extensions.admin import content, images


MODULE = 'pulp_docker.extensions.admin.content'


class TestDockerImageCopyCommand(unittest.TestCase):

    @mock.patch('pulp_docker.extensions.admin.images.get_formatter_for_type')
    def test_get_formatter_for_type(self, mock_formatter):
        context = mock.MagicMock()
        command = images.ImageCopyCommand(context)

        command.get_formatter_for_type('foo')
        mock_formatter.assert_called_once_with('foo')


class TestGetFormatterForType(unittest.TestCase):

    def test_call_with_image(self):
        formatter = images.get_formatter_for_type(constants.IMAGE_TYPE_ID)
        self.assertEquals('foo', formatter({'image_id': 'foo'}))

    def test_call_with_manifest(self):
        digest = '1234'
        formatter = content.get_formatter_for_type(constants.MANIFEST_TYPE_ID)
        unit = dict(digest=digest)
        self.assertEqual(formatter(unit), digest)

    def test_call_with_manifest_list(self):
        digest = '1234'
        formatter = content.get_formatter_for_type(constants.MANIFEST_LIST_TYPE_ID)
        unit = dict(digest=digest)
        self.assertEqual(formatter(unit), digest)

    def test_call_with_blob(self):
        digest = '1234'
        formatter = content.get_formatter_for_type(constants.BLOB_TYPE_ID)
        unit = dict(digest=digest)
        self.assertEqual(formatter(unit), digest)

    def test_call_invalid_type_id(self):
        self.assertRaises(ValueError, content.get_formatter_for_type, '')
        self.assertRaises(ValueError, content.get_formatter_for_type, 'foo-type')
        self.assertRaises(ValueError, images.get_formatter_for_type, '')
        self.assertRaises(ValueError, images.get_formatter_for_type, 'foo-type')


class TestImageRemoveCommand(unittest.TestCase):

    @mock.patch('pulp_docker.extensions.admin.images.get_formatter_for_type')
    def test_get_formatter_for_type(self, mock_formatter):
        context = mock.MagicMock()
        command = images.ImageRemoveCommand(context)

        command.get_formatter_for_type('foo')
        mock_formatter.assert_called_once_with('foo')


class TestImageSearchCommand(unittest.TestCase):

    def test_run(self):
        context = mock.MagicMock()
        command = images.ImageSearchCommand(context)

        repo_info = {
            u'scratchpad': {u'tags': [{constants.IMAGE_TAG_KEY: 'latest',
                                       constants.IMAGE_ID_KEY: 'bar'},
                                      {constants.IMAGE_TAG_KEY: 'foo',
                                       constants.IMAGE_ID_KEY: 'bar'}]}
        }
        context.server.repo.repository.return_value.response_body = repo_info

        image_list = [{u'metadata': {u'image_id': 'bar'}}]
        context.server.repo_unit.search.return_value.response_body = image_list

        command.run(**{'repo-id': 'baz'})
        target = copy.deepcopy(image_list)
        target[0][u'metadata'][u'tags'] = ['latest', 'foo']

        context.prompt.render_document_list.assert_called_once_with(target)


class TestManifestSearchCommand(unittest.TestCase):

    def test_init(self):
        context = mock.Mock()
        command = content.ManifestSearchCommand(context)
        self.assertEqual(command.context, context)
        self.assertEqual(command.name, 'manifest')
        self.assertEqual(command.prompt, context.prompt)
        self.assertFalse(command.description is None)
        self.assertEqual(command.method, command.run)

    def test_run(self):
        repo_id = '1234'
        context = mock.Mock()
        kwargs = {
            content.options.OPTION_REPO_ID.keyword: repo_id
        }
        command = content.ManifestSearchCommand(context)

        # test
        command.run(**kwargs)

        # validation
        context.server.repo_unit.search.assert_called_once_with(
            repo_id, type_ids=[constants.MANIFEST_TYPE_ID])
        context.prompt.render_document_list(
            context.server.repo_unit.search.return_value.response_body)


class TestManifestListSearchCommand(unittest.TestCase):

    def test_init(self):
        context = mock.Mock()
        command = content.ManifestListSearchCommand(context)
        self.assertEqual(command.context, context)
        self.assertEqual(command.name, 'manifest-list')
        self.assertEqual(command.prompt, context.prompt)
        self.assertFalse(command.description is None)
        self.assertEqual(command.method, command.run)

    def test_run(self):
        repo_id = '1234'
        context = mock.Mock()
        kwargs = {
            content.options.OPTION_REPO_ID.keyword: repo_id
        }
        command = content.ManifestListSearchCommand(context)

        # test
        command.run(**kwargs)

        # validation
        context.server.repo_unit.search.assert_called_once_with(
            repo_id, type_ids=[constants.MANIFEST_LIST_TYPE_ID])
        context.prompt.render_document_list(
            context.server.repo_unit.search.return_value.response_body)


class TestManifestCopyCommand(unittest.TestCase):

    def test_init(self):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestCopyCommand(context)
        self.assertEqual(command.name, 'manifest')
        self.assertFalse(command.description is None)
        self.assertEqual(command.context, context)
        self.assertEqual(command.method, command.run)

    @mock.patch(MODULE + '.get_formatter_for_type')
    def test_get_formatter_for_type(self, get_formatter):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestCopyCommand(context)
        formatter = command.get_formatter_for_type(constants.MANIFEST_TYPE_ID)
        self.assertEqual(formatter, get_formatter.return_value)


class TestManifestListCopyCommand(unittest.TestCase):

    def test_init(self):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestListCopyCommand(context)
        self.assertEqual(command.name, 'manifest-list')
        self.assertFalse(command.description is None)
        self.assertEqual(command.context, context)
        self.assertEqual(command.method, command.run)

    @mock.patch(MODULE + '.get_formatter_for_type')
    def test_get_formatter_for_type(self, get_formatter):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestListCopyCommand(context)
        formatter = command.get_formatter_for_type(constants.MANIFEST_LIST_TYPE_ID)
        self.assertEqual(formatter, get_formatter.return_value)


class TestManifestRemoveCommand(unittest.TestCase):

    def test_init(self):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestRemoveCommand(context)
        self.assertEqual(command.name, 'manifest')
        self.assertFalse(command.description is None)
        self.assertEqual(command.context, context)
        self.assertEqual(command.method, command.run)

    @mock.patch(MODULE + '.get_formatter_for_type')
    def test_get_formatter_for_type(self, get_formatter):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestRemoveCommand(context)
        formatter = command.get_formatter_for_type(constants.MANIFEST_TYPE_ID)
        self.assertEqual(formatter, get_formatter.return_value)


class TestManifestListRemoveCommand(unittest.TestCase):

    def test_init(self):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestListRemoveCommand(context)
        self.assertEqual(command.name, 'manifest-list')
        self.assertFalse(command.description is None)
        self.assertEqual(command.context, context)
        self.assertEqual(command.method, command.run)

    @mock.patch(MODULE + '.get_formatter_for_type')
    def test_get_formatter_for_type(self, get_formatter):
        context = mock.Mock(config={'output': {'poll_frequency_in_seconds': 10}})
        command = content.ManifestListRemoveCommand(context)
        formatter = command.get_formatter_for_type(constants.MANIFEST_LIST_TYPE_ID)
        self.assertEqual(formatter, get_formatter.return_value)
