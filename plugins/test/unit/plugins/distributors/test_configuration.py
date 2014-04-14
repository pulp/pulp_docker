import os
import shutil
import tempfile
import unittest

from mock import Mock
from pulp.common import error_codes
from pulp.devel.unit.server.util import assert_validation_exception

from pulp_docker.common import constants
from pulp_docker.plugins.distributors import configuration


class TestValidateConfig(unittest.TestCase):

    def test_relative_url_is_valid(self):
        config = {
            constants.CONFIG_KEY_RELATIVE_URL: 'foo'
        }
        self.assertEquals((True, None), configuration.validate_config(config))

    def test_relative_url_is_absolute(self):
        config = {
            constants.CONFIG_KEY_RELATIVE_URL: '/foo'
        }
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.PLP1006], config)

    def test_relative_url_references_parent_is_absolute(self):
        config = {
            constants.CONFIG_KEY_RELATIVE_URL: 'foo/../../quux'
        }
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.PLP1007], config)


class TestConfigurationGetters(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.publish_dir = os.path.join(self.working_directory, 'publish')
        self.repo_working = os.path.join(self.working_directory, 'work')

        self.repo = Mock(id='foo', working_dir=self.repo_working)
        self.config = {
            constants.CONFIG_KEY_DOCKER_PUBLISH_DIRECTORY: self.publish_dir
        }

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_get_root_publish_directory(self):
        directory = configuration.get_root_publish_directory(self.config)
        self.assertEquals(directory, self.publish_dir)

    def test_get_master_publish_dir(self):
        directory = configuration.get_master_publish_dir(self.repo, self.config)
        self.assertEquals(directory, os.path.join(self.publish_dir, 'master', self.repo.id))

    def test_get_web_publish_dir(self):
        directory = configuration.get_web_publish_dir(self.repo, self.config)
        self.assertEquals(directory, os.path.join(self.publish_dir, 'web', self.repo.id))

    def test_get_repo_relative_path(self):
        self.config[constants.CONFIG_KEY_RELATIVE_URL] = 'baz/bar'
        directory = configuration.get_repo_relative_path(self.repo, self.config)
        self.assertEquals(directory, 'baz/bar')

    def test_get_repo_relative_path_leading_slash(self):
        self.config[constants.CONFIG_KEY_RELATIVE_URL] = '/baz/bar'
        directory = configuration.get_repo_relative_path(self.repo, self.config)
        self.assertEquals(directory, 'baz/bar')

    def test_get_repo_relative_path_not_specified(self):
        directory = configuration.get_repo_relative_path(self.repo, self.config)
        self.assertEquals(directory, self.repo.id)
