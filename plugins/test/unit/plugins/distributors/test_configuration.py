import os
import shutil
import tempfile
import unittest

from mock import Mock, patch

from pulp.devel.unit.server.util import assert_validation_exception
from pulp.plugins.config import PluginCallConfiguration

from pulp_docker.common import constants, error_codes
from pulp_docker.plugins.distributors import configuration


class TestValidateConfig(unittest.TestCase):

    def test_server_url_fully_qualified(self):
        config = {
            constants.CONFIG_KEY_REDIRECT_URL: 'http://www.pulpproject.org/foo'
        }
        repo = Mock(id='nowthisisastory')
        self.assertEquals((True, None), configuration.validate_config(config, repo))

    def test_server_url_fully_qualified_with_port(self):
        config = {
            constants.CONFIG_KEY_REDIRECT_URL: 'http://www.pulpproject.org:440/foo'
        }
        repo = Mock(id='allabouthow')
        self.assertEquals((True, None), configuration.validate_config(config, repo))

    def test_server_url_empty(self):
        config = {
            constants.CONFIG_KEY_REDIRECT_URL: ''
        }
        repo = Mock(id='mylifegotflipturned')
        # This is valid as the default server should be used
        self.assertEquals((True, None), configuration.validate_config(config, repo))

    def test_server_url_missing_host_and_path(self):
        config = {
            constants.CONFIG_KEY_REDIRECT_URL: 'http://'
        }
        repo = Mock(id='upsidedown')
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1002,
                                     error_codes.DKR1003], config, repo)

    def test_server_url_missing_scheme(self):
        config = {
            constants.CONFIG_KEY_REDIRECT_URL: 'www.pulpproject.org/foo'
        }
        repo = Mock(id='andidliketotakeaminute')
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1001,
                                     error_codes.DKR1002], config, repo)

    def test_configuration_protected_true(self):
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_PROTECTED: True
        }, {})
        repo = Mock(id='justsitrightthere')
        self.assertEquals((True, None), configuration.validate_config(config, repo))

    def test_configuration_protected_false_str(self):
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_PROTECTED: 'false'
        }, {})
        repo = Mock(id='illtellyouhowibecametheprince')
        self.assertEquals((True, None), configuration.validate_config(config, repo))

    def test_configuration_protected_bad_str(self):
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_PROTECTED: 'apple'
        }, {})
        repo = Mock(id='ofatowncalledbellaire')
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1004], config, repo)

    def test_repo_regisrty_id_with_slash(self):
        """
        We need to allow a single slash in this field to allow namespacing.
        """
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_REPO_REGISTRY_ID: 'slashes/ok'
        }, {})
        repo = Mock(id='repoid')
        self.assertEquals((True, None), configuration.validate_config(config, repo))

    def test_repo_regisrty_id_with_multiple_slashes(self):
        """
        We need to allow only one slash.
        """
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_REPO_REGISTRY_ID: 'slashes/ok/notok'
        }, {})
        repo = Mock(id='repoid')
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1005], config, repo)

    def test_invalid_repo_registry_id(self):
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_REPO_REGISTRY_ID: 'noUpperCase'
        }, {})
        repo = Mock(id='repoid')
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1005], config, repo)

        config2 = PluginCallConfiguration({
            constants.CONFIG_KEY_REPO_REGISTRY_ID: 'Nouppsercase'
        }, {})
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1005], config2, repo)

    def test_invalid_default_repo_registry_id(self):
        config = PluginCallConfiguration({}, {})
        repo = Mock(id='InvalidRegistry')
        assert_validation_exception(configuration.validate_config,
                                    [error_codes.DKR1006], config, repo)

    def test_invalid_default_valid_override_repo_registry_id(self):
        config = PluginCallConfiguration({
            constants.CONFIG_KEY_REPO_REGISTRY_ID: 'valid'
        }, {})
        repo = Mock(id='ValidRepoInvalidRegistry')
        try:
            configuration.validate_config(config, repo)
        except Exception, e:
            self.fail(
                'validate_config unexpectedly raised: {exception}'.format(exception=type(e))
            )

    def test__is_valid_repo_registry_id(self):
        """
        Test repo regisrty id validation
        """
        should_be_valid = [
            'lowercase',
            'lower-case',
            'lower_case',
            '134567890',
            'alpha-numeric_123',
            'periods.are.cool',
            '..............',
        ]
        should_not_be_valid = [
            'things with spaces',
            'UPPERCASE',
            'Uppercase',
            'upperCase',
            'uppercasE',
            '$ymbols',
            '$tuff.th@t.m!ght.h@ve.w%!rd.r#g#x.m*anings()'
        ]
        for candidate in should_be_valid:
            valid = configuration._is_valid_repo_registry_id(candidate)
            self.assertTrue(valid)
            self.assertEqual(bool, type(valid))

        for candidate in should_not_be_valid:
            valid = configuration._is_valid_repo_registry_id(candidate)
            self.assertFalse(valid)
            self.assertEqual(bool, type(valid))


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
        directory = configuration.get_root_publish_directory(self.config, 'v2')
        self.assertEquals(directory, os.path.join(self.publish_dir, 'v2'))

    def test_get_master_publish_dir(self):
        directory = configuration.get_master_publish_dir(self.repo, self.config, 'v2')
        self.assertEquals(directory, os.path.join(self.publish_dir, 'v2', 'master', self.repo.id))

    def test_get_web_publish_dir(self):
        directory = configuration.get_web_publish_dir(self.repo, self.config, 'v2')
        self.assertEquals(directory, os.path.join(self.publish_dir, 'v2', 'web', self.repo.id))

    def test_get_repo_relative_path(self):
        directory = configuration.get_repo_relative_path(self.repo, self.config)
        self.assertEquals(directory, self.repo.id)

    def test_get_redirect_url_from_config(self):
        sample_url = 'http://www.pulpproject.org/'
        conduit = Mock(repo_id=sample_url)
        url = configuration.get_redirect_url({constants.CONFIG_KEY_REDIRECT_URL: sample_url},
                                             conduit)
        self.assertEquals(sample_url, url)

    def test_get_redirect_url_from_config_trailing_slash(self):
        sample_url = 'http://www.pulpproject.org'
        conduit = Mock(repo_id=sample_url)
        url = configuration.get_redirect_url({constants.CONFIG_KEY_REDIRECT_URL: sample_url},
                                             conduit)
        self.assertEquals(sample_url + '/', url)

    @patch('pulp_docker.plugins.distributors.configuration.server_config')
    def test_get_redirect_url_generated(self, mock_server_config):
        mock_server_config.get.return_value = 'www.foo.bar'
        computed_result = 'https://www.foo.bar/pulp/docker/baz/'
        self.assertEquals(computed_result, configuration.get_redirect_url({},
                                                                          Mock(id='baz')))

    def test_get_export_repo_filename(self):
        filename = configuration.get_export_repo_filename(self.repo, self.config)
        self.assertEquals(filename, "foo.tar")

    def test_get_export_repo_directory(self):
        directory = configuration.get_export_repo_directory(self.config, 'v1')
        self.assertEquals(directory, os.path.join(self.publish_dir, 'v1', 'export', 'repo'))

    def test_get_export_repo_file_with_path_from_config(self):
        config = PluginCallConfiguration(None, {constants.CONFIG_KEY_EXPORT_FILE: '/tmp/foo.tar'})
        result = configuration.get_export_repo_file_with_path(self.repo, config, 'v1')
        self.assertEquals(result, '/tmp/foo.tar')

    def test_get_export_repo_file_with_path_default(self):
        result = configuration.get_export_repo_file_with_path(self.repo, self.config, 'v1')
        expected_result = os.path.join(configuration.get_export_repo_directory(self.config, 'v1'),
                                       configuration.get_export_repo_filename(self.repo,
                                                                              self.config))
        self.assertEquals(result, expected_result)
