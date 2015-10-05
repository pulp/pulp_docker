import shutil
import tempfile
import unittest

from mock import Mock, call
from pulp.common.compat import json
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db.models import Repository

from pulp_docker.common import constants
from pulp_docker.plugins.db import models
from pulp_docker.plugins.distributors import metadata


class TestRedirectFileContext(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.repo = Repository(repo_id='foo_repo_id')
        self.config = PluginCallConfiguration(None, None)
        self.conduit = RepoPublishConduit(self.repo.id, 'foo_repo')
        self.conduit.get_repo_scratchpad = Mock(return_value={u'tags': []})
        tag_list = [{constants.IMAGE_TAG_KEY: u'latest',
                     constants.IMAGE_ID_KEY: u'image_id'}]
        self.conduit.get_repo_scratchpad.return_value = {u'tags': tag_list}
        self.context = metadata.RedirectFileContext(self.working_directory,
                                                    self.conduit,
                                                    self.config,
                                                    self.repo)
        self.context.metadata_file_handle = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_add_unit_metadata(self):
        unit = models.DockerImage(image_id='foo_image', parent_id='foo_parent', size=2048)
        test_result = {'id': 'foo_image'}
        result_json = json.dumps(test_result)
        self.context.add_unit_metadata(unit)
        self.context.metadata_file_handle.write.assert_called_once_with(result_json)

    def test_add_unit_metadata_with_tag(self):
        unit = models.DockerImage(image_id='foo_image', parent_id='foo_parent', size=2048)
        test_result = {'id': 'foo_image'}
        result_json = json.dumps(test_result)
        self.context.tags = {'bar': 'foo_image'}
        self.context.redirect_url = 'http://www.pulpproject.org/foo/'
        self.context.add_unit_metadata(unit)
        self.context.metadata_file_handle.write.assert_called_once_with(result_json)

    def test_write_file_header(self):
        self.context.repo_id = 'bar'
        self.context.redirect_url = 'http://www.pulpproject.org/foo/'

        self.context._write_file_header()
        result_string = '{"type":"pulp-docker-redirect","version":1,"repository":"bar",' \
                        '"repo-registry-id": "foo_repo_id",' \
                        '"url":"http://www.pulpproject.org/foo/",' \
                        '"protected":false,"images":['
        self.context.metadata_file_handle.write.assert_called_once_with(result_string)

    def test_write_file_protected_true(self):
        self.config = PluginCallConfiguration(None, {'protected': True})
        self.context = metadata.RedirectFileContext(self.working_directory,
                                                    self.conduit,
                                                    self.config,
                                                    self.repo)
        self.context.metadata_file_handle = Mock()
        self.context.repo_id = 'bar'
        self.context.redirect_url = 'http://www.pulpproject.org/foo/'

        self.context._write_file_header()
        result_string = '{"type":"pulp-docker-redirect","version":1,"repository":"bar",' \
                        '"repo-registry-id": "foo_repo_id",' \
                        '"url":"http://www.pulpproject.org/foo/",' \
                        '"protected":true,"images":['
        self.context.metadata_file_handle.write.assert_called_once_with(result_string)

    def test_write_file_footer(self):
        self.context._write_file_footer()
        calls = [call('],"tags":'), call(json.dumps({u'latest': u'image_id'})), call('}')]

        self.context.metadata_file_handle.write.assert_has_calls(calls)

    def test_convert_tag_list_to_dict(self):
        self.assertEqual(self.context.convert_tag_list_to_dict([]), {})
        tag_list = [{constants.IMAGE_TAG_KEY: 'tag1',
                     constants.IMAGE_ID_KEY: 'image1'},
                    {constants.IMAGE_TAG_KEY: 'tag2',
                     constants.IMAGE_ID_KEY: 'image2'}]
        tag_dict = self.context.convert_tag_list_to_dict(tag_list)
        expected_tag_dict = {'tag1': 'image1', 'tag2': 'image2'}
        self.assertEqual(tag_dict, expected_tag_dict)
