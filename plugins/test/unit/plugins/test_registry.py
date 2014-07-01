from cStringIO import StringIO
import json
import os
import tempfile
import unittest

import mock
from nectar.config import DownloaderConfig
from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.report import DownloadReport
from nectar.request import DownloadRequest
import shutil

from pulp_docker.plugins import registry


class TestInit(unittest.TestCase):
    def test_init(self):
        config = DownloaderConfig()
        repo = registry.Repository('pulp/crane', config, 'http://pulpproject.org/', '/a/b/c')

        self.assertEqual(repo.name, 'pulp/crane')
        self.assertEqual(repo.registry_url, 'http://pulpproject.org/')
        self.assertEqual(repo.working_dir, '/a/b/c')
        self.assertTrue(isinstance(repo.downloader, HTTPThreadedDownloader))


class TestGetSinglePath(unittest.TestCase):
    def setUp(self):
        super(TestGetSinglePath, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.Repository('pulp/crane', self.config,
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


class TestGetImageIDs(unittest.TestCase):
    def setUp(self):
        super(TestGetImageIDs, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.Repository('pulp/crane', self.config,
                                        'http://pulpproject.org/', '/a/b/c')

    def test_returns_ids(self):
        with mock.patch.object(self.repo, '_get_single_path') as mock_get:
            mock_get.return_value = [{'id': 'abc123'}]

            ret = self.repo.get_image_ids()

        self.assertEqual(ret, ['abc123'])
        mock_get.assert_called_once_with('/v1/repositories/pulp/crane/images')


class TestGetTags(unittest.TestCase):
    def setUp(self):
        super(TestGetTags, self).setUp()
        self.config = DownloaderConfig()
        self.repo = registry.Repository('pulp/crane', self.config,
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
        self.repo = registry.Repository('pulp/crane', self.config,
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
        self.repo = registry.Repository('pulp/crane', self.config,
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
        self.repo = registry.Repository('pulp/crane', self.config,
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
