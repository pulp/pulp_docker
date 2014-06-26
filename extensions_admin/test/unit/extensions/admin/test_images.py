import copy
import unittest

from mock import MagicMock, patch

from pulp_docker.common import constants
from pulp_docker.extensions.admin import images


class TestDockerImageCopyCommand(unittest.TestCase):

    @patch('pulp_docker.extensions.admin.images.get_formatter_for_type')
    def test_get_formatter_for_type(self, mock_formatter):
        context = MagicMock()
        command = images.ImageCopyCommand(context)

        command.get_formatter_for_type('foo')
        mock_formatter.assert_called_once_with('foo')


class TestGetFormatterForType(unittest.TestCase):

    def test_get_formatter_for_type(self):
        formatter = images.get_formatter_for_type(constants.IMAGE_TYPE_ID)
        self.assertEquals('foo', formatter({'image_id': 'foo'}))

    def test_get_formatter_for_type_raises_value_error(self):
        self.assertRaises(ValueError, images.get_formatter_for_type, 'foo-type')


class TestImageRemoveCommand(unittest.TestCase):

    @patch('pulp_docker.extensions.admin.images.get_formatter_for_type')
    def test_get_formatter_for_type(self, mock_formatter):
        context = MagicMock()
        command = images.ImageRemoveCommand(context)

        command.get_formatter_for_type('foo')
        mock_formatter.assert_called_once_with('foo')


class TestImageSearchCommand(unittest.TestCase):

    def test_run(self):
        context = MagicMock()
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
