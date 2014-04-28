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
