from cStringIO import StringIO
import httplib
import json
import os
import shutil
import tempfile

import mock
from nectar.config import DownloaderConfig
from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.report import DownloadReport
from nectar.request import DownloadRequest
from pulp.common.compat import unittest
from pulp.server.exceptions import PulpCodedException

from pulp_docker.common import error_codes
from pulp_docker.plugins import registry


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


class TestInit(unittest.TestCase):
    def test_init(self):
        config = DownloaderConfig()
        repo = registry.V1Repository('pulp/crane', config, 'http://pulpproject.org/', '/a/b/c')

        self.assertEqual(repo.name, 'pulp/crane')
        self.assertEqual(repo.registry_url, 'http://pulpproject.org/')
        self.assertEqual(repo.working_dir, '/a/b/c')
        self.assertTrue(isinstance(repo.downloader, HTTPThreadedDownloader))


class TestGetSinglePath(unittest.TestCase):
    def setUp(self):
        super(TestGetSinglePath, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', '/a/b/c')

    @mock.patch.object(HTTPThreadedDownloader, 'download_one')
    def test_get_tags(self, mock_download_one):
        body = json.dumps({'latest': 'abc123'})
        report = DownloadReport('http://pulpproject.org/v1/repositories/pulp/crane/tags',
                                StringIO(body))
        report.headers = {}
        mock_download_one.return_value = report

        ret = self.repo._get_single_path('/v1/repositories/pulp/crane/tags')

        self.assertEqual(ret, {'latest': 'abc123'})
        self.assertEqual(mock_download_one.call_count, 1)
        self.assertTrue(isinstance(mock_download_one.call_args[0][0], DownloadRequest))
        req = mock_download_one.call_args[0][0]
        self.assertEqual(req.url, 'http://pulpproject.org/v1/repositories/pulp/crane/tags')

    @mock.patch.object(HTTPThreadedDownloader, 'download_one')
    def test_get_tags_from_endpoint(self, mock_download_one):
        body = json.dumps({'latest': 'abc123'})
        report = DownloadReport('http://some-endpoint.org/v1/repositories/pulp/crane/tags',
                                StringIO(body))
        report.headers = {}
        mock_download_one.return_value = report
        self.repo.endpoint = 'some-endpoint.org'
        # this lets us test that auth was added to the request
        self.repo.token = 'letmein'

        ret = self.repo._get_single_path('/v1/repositories/pulp/crane/tags')

        self.assertEqual(ret, {'latest': 'abc123'})
        self.assertEqual(mock_download_one.call_count, 1)
        self.assertTrue(isinstance(mock_download_one.call_args[0][0], DownloadRequest))
        req = mock_download_one.call_args[0][0]
        self.assertEqual(req.url, 'http://some-endpoint.org/v1/repositories/pulp/crane/tags')
        # make sure the authorization was added, which is usually required by an endpoint
        self.assertTrue('Authorization' in req.headers)

    @mock.patch.object(HTTPThreadedDownloader, 'download_one')
    def test_get_tags_from_ssl_endpoint(self, mock_download_one):
        body = json.dumps({'latest': 'abc123'})
        report = DownloadReport('https://some-endpoint.org/v1/repositories/pulp/crane/tags',
                                StringIO(body))
        report.headers = {}
        mock_download_one.return_value = report
        self.repo.endpoint = 'some-endpoint.org'
        self.repo.registry_url = 'https://pulpproject.org/'
        # this lets us test that auth was added to the request
        self.repo.token = 'letmein'

        ret = self.repo._get_single_path('/v1/repositories/pulp/crane/tags')

        self.assertEqual(ret, {'latest': 'abc123'})
        self.assertEqual(mock_download_one.call_count, 1)
        self.assertTrue(isinstance(mock_download_one.call_args[0][0], DownloadRequest))
        req = mock_download_one.call_args[0][0]
        self.assertEqual(req.url, 'https://some-endpoint.org/v1/repositories/pulp/crane/tags')
        # make sure the authorization was added, which is usually required by an endpoint
        self.assertTrue('Authorization' in req.headers)

    @mock.patch.object(HTTPThreadedDownloader, 'download_one')
    def test_get_images(self, mock_download_one):
        body = json.dumps(['abc123'])
        report = DownloadReport('http://pulpproject.org/v1/repositories/pulp/crane/images',
                                StringIO(body))
        report.headers = {}
        mock_download_one.return_value = report

        ret = self.repo._get_single_path('/v1/repositories/pulp/crane/images')

        self.assertEqual(ret, ['abc123'])
        self.assertEqual(mock_download_one.call_count, 1)
        self.assertTrue(isinstance(mock_download_one.call_args[0][0], DownloadRequest))
        req = mock_download_one.call_args[0][0]
        self.assertEqual(req.url, 'http://pulpproject.org/v1/repositories/pulp/crane/images')
        # make sure this header is set, which is required by the docker API in order
        # to give us an auth token
        self.assertEqual(req.headers[self.repo.DOCKER_TOKEN_HEADER], 'true')

    @mock.patch.object(HTTPThreadedDownloader, 'download_one')
    def test_get_with_headers(self, mock_download_one):
        body = json.dumps(['abc123'])
        report = DownloadReport('http://pulpproject.org/v1/repositories/pulp/crane/images',
                                StringIO(body))
        report.headers = {
            self.repo.DOCKER_TOKEN_HEADER: 'token',
            self.repo.DOCKER_ENDPOINT_HEADER: 'endpoint',
        }
        mock_download_one.return_value = report

        self.repo._get_single_path('/v1/repositories/pulp/crane/images')

        self.assertEqual(self.repo.token, 'token')
        self.assertEqual(self.repo.endpoint, 'endpoint')

    @mock.patch.object(HTTPThreadedDownloader, 'download_one')
    def test_get_single_path_failure(self, mock_download_one):
        report = DownloadReport('http://pulpproject.org/v1/repositories/pulp/crane/images',
                                StringIO(''))
        report.headers = {}
        report.state = report.DOWNLOAD_FAILED
        mock_download_one.return_value = report

        self.assertRaises(IOError, self.repo._get_single_path, '/v1/repositories/pulp/crane/images')


class TestAPIVersionCheck(unittest.TestCase):
    def setUp(self):
        super(TestAPIVersionCheck, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', '/a/b/c')

    @mock.patch.object(registry.V1Repository, '_get_single_path')
    def test_success(self, mock_get_path):
        ret = self.repo.api_version_check()

        self.assertTrue(ret)
        mock_get_path.assert_called_once_with(self.repo.API_VERSION_CHECK_PATH)

    @mock.patch.object(registry.V1Repository, '_get_single_path', spec_set=True)
    def test_error(self, mock_get_path):
        mock_get_path.side_effect = IOError
        ret = self.repo.api_version_check()

        self.assertFalse(ret)


class TestGetImageIDs(unittest.TestCase):
    def setUp(self):
        super(TestGetImageIDs, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', '/a/b/c')

    def test_returns_ids(self):
        with mock.patch.object(self.repo, '_get_single_path') as mock_get:
            mock_get.return_value = [{'id': 'abc123'}]

            ret = self.repo.get_image_ids()

        self.assertEqual(ret, ['abc123'])
        mock_get.assert_called_once_with('/v1/repositories/pulp/crane/images')

    def test_ioerror(self):
        with mock.patch.object(self.repo, '_get_single_path') as mock_get:
            mock_get.side_effect = IOError

            with self.assertRaises(PulpCodedException) as assertion:
                self.repo.get_image_ids()

            self.assertEqual(assertion.exception.error_code, error_codes.DKR1007)


class TestGetTags(unittest.TestCase):
    def setUp(self):
        super(TestGetTags, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', '/a/b/c')

    def test_returns_tags_as_dict(self):
        with mock.patch.object(self.repo, '_get_single_path') as mock_get:
            mock_get.return_value = {'latest': 'abc123'}

            ret = self.repo.get_tags()

        self.assertEqual(ret, {'latest': 'abc123'})
        mock_get.assert_called_once_with('/v1/repositories/pulp/crane/tags')

    def test_returns_tags_as_list(self):
        with mock.patch.object(self.repo, '_get_single_path') as mock_get:
            mock_get.return_value = [{'name': 'latest', 'layer': 'abc123'}]

            ret = self.repo.get_tags()

        self.assertEqual(ret, {'latest': 'abc123'})
        mock_get.assert_called_once_with('/v1/repositories/pulp/crane/tags')

    def test_adds_library_namespace(self):
        self.repo.name = 'crane'
        with mock.patch.object(self.repo, '_get_single_path') as mock_get:
            mock_get.return_value = {'latest': 'abc123'}

            self.repo.get_tags()

        # make sure the "library" part of the path was added, which is a required
        # quirk of the docker registry API
        mock_get.assert_called_once_with('/v1/repositories/library/crane/tags')


class TestGetAncestry(unittest.TestCase):
    def setUp(self):
        super(TestGetAncestry, self).setUp()
        self.working_dir = tempfile.mkdtemp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', self.working_dir)

    def tearDown(self):
        super(TestGetAncestry, self).tearDown()
        shutil.rmtree(self.working_dir)

    def test_with_no_images(self):
        with mock.patch.object(self.repo.downloader, 'download') as mock_download:
            self.repo.get_ancestry([])

        mock_download.assert_called_once_with([])

    def test_makes_destination_dir(self):
        with mock.patch.object(self.repo.downloader, 'download'):
            self.repo.get_ancestry(['abc123'])

        self.assertTrue(os.path.isdir(os.path.join(self.working_dir, 'abc123')))

    def test_dir_already_exists(self):
        with mock.patch.object(self.repo.downloader, 'download'):
            self.repo.get_ancestry(['abc123'])

        self.assertTrue(os.path.isdir(os.path.join(self.working_dir, 'abc123')))

    def test_error_making_dir(self):
        self.repo.working_dir = '/a/b/c'
        # this should be a permission denied error, which should be allowed to bubble up
        self.assertRaises(OSError, self.repo.get_ancestry, ['abc123'])

    def test_makes_request(self):
        with mock.patch.object(self.repo.downloader, 'download') as mock_download:
            self.repo.get_ancestry(['abc123'])

        self.assertEqual(mock_download.call_count, 1)
        self.assertEqual(len(mock_download.call_args[0][0]), 1)
        req = mock_download.call_args[0][0][0]
        self.assertEqual(req.url, 'http://pulpproject.org/v1/images/abc123/ancestry')
        self.assertEqual(req.destination, os.path.join(self.working_dir, 'abc123/ancestry'))

    def test_adds_auth_header(self):
        self.repo.token = 'letmein'
        with mock.patch.object(self.repo.downloader, 'download') as mock_download:
            self.repo.get_ancestry(['abc123'])

        self.assertEqual(mock_download.call_count, 1)
        self.assertEqual(len(mock_download.call_args[0][0]), 1)
        req = mock_download.call_args[0][0][0]
        self.assertEqual(req.headers['Authorization'], 'Token letmein')

    def test_uses_endpoint(self):
        self.repo.endpoint = 'redhat.com'
        with mock.patch.object(self.repo.downloader, 'download') as mock_download:
            self.repo.get_ancestry(['abc123'])

        self.assertEqual(mock_download.call_count, 1)
        self.assertEqual(len(mock_download.call_args[0][0]), 1)
        req = mock_download.call_args[0][0][0]
        self.assertEqual(req.url, 'http://redhat.com/v1/images/abc123/ancestry')

    def test_failed_request(self):
        self.repo.listener.failed_reports.append(
            DownloadReport('http://redhat.com/v1/images/abc123/ancestry', '/a/b/c'))
        with mock.patch.object(self.repo.downloader, 'download'):
            self.assertRaises(IOError, self.repo.get_ancestry, ['abc123'])


class TestAddAuthHeader(unittest.TestCase):
    def setUp(self):
        super(TestAddAuthHeader, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', '/a/b/')
        self.request = DownloadRequest('http://pulpproject.org', '/a/b/c')

    def test_add_token(self):
        self.repo.token = 'letmein'

        self.repo.add_auth_header(self.request)

        self.assertEqual(self.request.headers['Authorization'], 'Token letmein')

    def test_without_token(self):
        self.request.headers = {}
        self.repo.add_auth_header(self.request)

        self.assertTrue('Authorization' not in self.request.headers)

    def test_does_not_clobber_other_headers(self):
        self.repo.token = 'letmein'
        self.request.headers = {'foo': 'bar'}

        self.repo.add_auth_header(self.request)

        self.assertEqual(self.request.headers['Authorization'], 'Token letmein')
        self.assertEqual(self.request.headers['foo'], 'bar')


class TestGetImageURL(unittest.TestCase):
    def setUp(self):
        super(TestGetImageURL, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.V1Repository('pulp/crane', self.config,
                                          'http://pulpproject.org/', '/a/b/')

    def test_without_endpoint(self):
        url = self.repo.get_image_url()

        self.assertEqual(url, self.repo.registry_url)

    def test_with_endpoint(self):
        self.repo.endpoint = 'redhat.com'

        url = self.repo.get_image_url()

        self.assertEqual(url, 'http://redhat.com/')

    def test_preserves_https(self):
        self.repo.registry_url = 'https://pulpproject.org/'
        self.repo.endpoint = 'redhat.com'

        url = self.repo.get_image_url()

        self.assertEqual(url, 'https://redhat.com/')


class TestV2Repository(unittest.TestCase):
    """
    This class contains tests for the V2Repository class. The Docker v2 API is described here:

    https://github.com/docker/distribution/blob/release/2.0/docs/spec/api.md
    """
    def test___init__(self):
        """
        Assert that __init__() initializes all the correct attributes.
        """
        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)

        self.assertEqual(r.name, name)
        self.assertEqual(r.download_config, download_config)
        self.assertEqual(r.registry_url, registry_url)
        self.assertEqual(type(r.downloader), HTTPThreadedDownloader)
        self.assertEqual(r.downloader.config, download_config)
        self.assertEqual(r.working_dir, working_dir)

    def test_api_version_check_incorrect_header(self):
        """
        The the api_version_check() method when the response has the Docker-Distribution-API-Version
        header, but it is not the correct value for a Docker v2 registry.
        """
        def download_one(request):
            """
            Mock the download_one() method to manipulate the path.
            """
            self.assertEqual(request.url, 'https://registry.example.com/v2/')
            self.assertEqual(type(request.destination), type(StringIO()))
            report = DownloadReport(request.url, request.destination)
            report.download_succeeded()
            report.headers = {'Docker-Distribution-API-Version': 'WRONG_VALUE!'}
            report.destination.write("")
            return report

        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        r.downloader.download_one = mock.MagicMock(side_effect=download_one)

        self.assertFalse(r.api_version_check())

    @mock.patch('pulp_docker.plugins.registry.V2Repository._get_path', side_effect=IOError)
    def test_api_version_check_ioerror(self, mock_get_path):
        """
        The the api_version_check() method when _get_path() raises an IOError.
        """
        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)

        self.assertFalse(r.api_version_check())

    def test_api_version_check_missing_header(self):
        """
        The the api_version_check() method when the response is missing the
        Docker-Distribution-API-Version header. Since we want to support servers that are just
        serving simple directories of files, it should be OK if the header is not present.
        """
        def download_one(request):
            """
            Mock the download_one() method to manipulate the path.
            """
            self.assertEqual(request.url, 'https://registry.example.com/v2/')
            self.assertEqual(type(request.destination), type(StringIO()))
            report = DownloadReport(request.url, request.destination)
            report.download_succeeded()
            # The Version header is not present
            report.headers = {}
            report.destination.write("")
            return report

        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        r.downloader.download_one = mock.MagicMock(side_effect=download_one)

        # This should not raise an Exception
        r.api_version_check()

    def test_api_version_check_successful(self):
        """
        The the api_version_check() method when the registry_url is indeed a Docker v2 registry.
        """
        def download_one(request):
            """
            Mock the download_one() method to manipulate the path.
            """
            self.assertEqual(request.url, 'https://registry.example.com/v2/')
            self.assertEqual(type(request.destination), type(StringIO()))
            report = DownloadReport(request.url, request.destination)
            report.download_succeeded()
            report.headers = {'Docker-Distribution-API-Version': 'registry/2.0'}
            report.destination.write("")
            return report

        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        r.downloader.download_one = mock.MagicMock(side_effect=download_one)

        # This should not raise an Exception
        r.api_version_check()

    def test_class_attributes(self):
        """
        Assert the correct class attributes.
        """
        self.assertEqual(registry.V2Repository.API_VERSION_CHECK_PATH, '/v2/')
        self.assertEqual(registry.V2Repository.LAYER_PATH, '/v2/{name}/blobs/{digest}')
        self.assertEqual(registry.V2Repository.MANIFEST_PATH, '/v2/{name}/manifests/{reference}')
        self.assertEqual(registry.V2Repository.TAGS_PATH, '/v2/{name}/tags/list')

    def test_create_blob_download_request(self):
        """
        Assert correct behavior from create_blob_download_request().
        """
        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        digest = 'sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef'

        request = r.create_blob_download_request(digest)

        self.assertEqual(request.url,
                         'https://registry.example.com/v2/pulp/blobs/{0}'.format(digest))
        self.assertEqual(request.destination, os.path.join(working_dir, digest))

    def test_get_manifest(self):
        """
        Assert correct behavior from get_manifest().
        """
        def download_one(request):
            """
            Mock the download_one() method to manipulate the path.
            """
            self.assertEqual(request.url,
                             'https://registry.example.com/v2/pulp/manifests/best_version_ever')
            self.assertEqual(type(request.destination), type(StringIO()))
            report = DownloadReport(request.url, request.destination)
            report.download_succeeded()
            schema2 = 'application/vnd.docker.distribution.manifest.v2+json'
            report.headers = {'Docker-Distribution-API-Version': 'registry/2.0',
                              'docker-content-digest': digest,
                              'content-type': schema2}
            report.destination.write(manifest)
            return report

        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        r.downloader.download_one = mock.MagicMock(side_effect=download_one)
        digest = 'sha256:46356a7d9575b4cee21e7867b1b83a51788610b7719a616096d943b44737ad9a'
        with open(os.path.join(TEST_DATA_PATH, 'manifest_repeated_layers.json')) as manifest_file:
            manifest = manifest_file.read()

        schema2 = 'application/vnd.docker.distribution.manifest.v2+json'
        m = r.get_manifest('best_version_ever', None, None)

        self.assertEqual([(manifest, digest, schema2)], m)

    def test_get_tags(self):
        """
        Assert correct behavior from get_tags().
        """
        def download_one(request):
            """
            Mock the download_one() method to manipulate the path.
            """
            self.assertEqual(request.url, 'https://registry.example.com/v2/pulp/tags/list')
            self.assertEqual(type(request.destination), type(StringIO()))
            report = DownloadReport(request.url, request.destination)
            report.download_succeeded()
            report.headers = {}
            report.destination.write('{"name": "pulp", "tags": ["best_ever", "latest", "decent"]}')
            return report

        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        r.downloader.download_one = mock.MagicMock(side_effect=download_one)

        tags = r.get_tags()

        self.assertEqual(tags, ["best_ever", "latest", "decent"])

    @mock.patch('pulp_docker.plugins.registry.V2Repository._get_path', side_effect=IOError)
    def test_get_tags_failed(self, mock_download_one):
        """
        When get_tags fails, make sure the correct exception is raised.
        """
        name = 'pulp'
        download_config = DownloaderConfig()
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)

        with self.assertRaises(PulpCodedException) as assertion:
            r.get_tags()

        self.assertEqual(assertion.exception.error_code, error_codes.DKR1007)

    @mock.patch('pulp_docker.plugins.auth_util.request_token')
    @mock.patch('pulp_docker.plugins.registry.HTTPThreadedDownloader.download_one')
    def test__get_path_failed(self, mock_download_one, mock_request_token):
        """
        Test _get_path() for the case when an IOError is raised by the downloader.
        """
        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)

        report = DownloadReport(registry_url + '/some/path', StringIO())
        report.error_report['response_code'] = httplib.UNAUTHORIZED
        report.state = DownloadReport.DOWNLOAD_FAILED
        report.headers = {}
        mock_download_one.return_value = report

        # The request will fail because the requested path does not exist
        self.assertRaises(IOError, r._get_path, '/some/path')

    def test__get_path_success(self):
        """
        Test _get_path() for the case when the download is successful.
        """
        def download_one(request):
            """
            Mock the download_one() method.
            """
            self.assertEqual(request.url, 'https://registry.example.com/some/path')
            self.assertEqual(type(request.destination), type(StringIO()))
            report = DownloadReport(request.url, request.destination)
            report.download_succeeded()
            report.headers = {'some': 'cool stuff'}
            report.destination.write("This is the stuff you've been waiting for.")
            return report

        name = 'pulp'
        download_config = DownloaderConfig(max_concurrent=25)
        registry_url = 'https://registry.example.com'
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        r.downloader.download_one = mock.MagicMock(side_effect=download_one)

        headers, body = r._get_path('/some/path')

        self.assertEqual(headers, {'some': 'cool stuff'})
        self.assertEqual(body, "This is the stuff you've been waiting for.")

    def test__raise_path_error_not_found(self):
        """
        For a standard error like 404, the report's error message should be used.
        """
        report = DownloadReport('http://foo/bar', '/a/b/c')
        report.error_report = {'response_code': httplib.NOT_FOUND}
        report.error_msg = 'oops'

        with self.assertRaises(IOError) as assertion:
            registry.V2Repository._raise_path_error(report)

        self.assertEqual(assertion.exception.message,
                         '404 Client Error: \'oops\' for url: http://foo/bar')

    def test__raise_path_server_error(self):
        """
        For server errors a slightly different message should be used.
        """
        report = DownloadReport('http://foo/bar', '/a/b/c')
        report.error_report = {'response_code': httplib.INTERNAL_SERVER_ERROR}
        report.error_msg = 'oops'

        with self.assertRaises(IOError) as assertion:
            registry.V2Repository._raise_path_error(report)

        self.assertEqual(assertion.exception.message,
                         '500 Server Error: \'oops\' for url: http://foo/bar')

    def test__raise_path_error_unathorized(self):
        """
        Specifically for a 401, a custom error message should be used explaining that the cause
        could be either that the client is unauthorized, or that the resource was not found.
        Docker hub responds 401 for the not found case, which is why this function exists.
        """
        report = DownloadReport('http://foo/bar', '/a/b/c')
        report.error_report = {'response_code': httplib.UNAUTHORIZED}
        report.error_msg = 'oops'

        with self.assertRaises(IOError) as assertion:
            registry.V2Repository._raise_path_error(report)

        # not worrying about what the exact contents are; just that the function added its
        # own message
        self.assertEqual(assertion.exception.message,
                         '401 Client Error: \'Unauthorized or Not Found\' for url http://foo/bar')
        self.assertTrue(len(assertion.exception.message) > 0)

    @mock.patch('pulp_docker.plugins.registry.HTTPThreadedDownloader')
    def test_dockerhub_v2_registry_without_namespace(self, http_threaded_downloader):
        name = 'test_image'
        registry_url = "https://registry-1.docker.io"
        download_config = mock.MagicMock()
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        self.assertEqual('library/test_image', r.name, "Non-name-spaced image not prepended")

    @mock.patch('pulp_docker.plugins.registry.HTTPThreadedDownloader')
    def test_dockerhub_v2_registry_with_namespace(self, http_threaded_downloader):
        name = 'library/test_image'
        registry_url = "https://registry-1.docker.io"
        download_config = mock.MagicMock()
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        self.assertNotEqual('library/library/test_image', r.name,
                            "Name-spaced image prepended with library")

    @mock.patch('pulp_docker.plugins.registry.HTTPThreadedDownloader')
    def test_non_dockerhub_v2_registry_with_namespace(self, http_threaded_downloader):
        name = 'library/test_image'
        registry_url = "https://somewhere.not-docker.io"
        download_config = mock.MagicMock()
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        self.assertNotEqual('library/library/test_image', r.name,
                            "Name-spaced Non-docker hub image prepended with library")

    @mock.patch('pulp_docker.plugins.registry.HTTPThreadedDownloader')
    def test_non_dockerhub_v2_registry_without_namespace(self, http_threaded_downloader):
        name = 'test_image'
        registry_url = "https://somewhere.not-docker.io"
        download_config = mock.MagicMock()
        working_dir = '/a/working/dir'
        r = registry.V2Repository(name, download_config, registry_url, working_dir)
        self.assertNotEqual('library/test_image', r.name,
                            "Non-docker hub image prepended with library")
