from cStringIO import StringIO
from gettext import gettext as _
import errno
import json
import logging
import os
import urlparse

from nectar.downloaders.threaded import HTTPThreadedDownloader
from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest

from pulp_docker.common import models


_logger = logging.getLogger(__name__)


class V1Repository(object):
    """
    This class represents a Docker v1 repository.
    """
    ANCESTRY_PATH = '/v1/images/%s/ancestry'
    DOCKER_TOKEN_HEADER = 'x-docker-token'
    DOCKER_ENDPOINT_HEADER = 'x-docker-endpoints'
    IMAGES_PATH = '/v1/repositories/%s/images'
    TAGS_PATH = '/v1/repositories/%s/tags'
    API_VERSION_CHECK_PATH = '/v1/_ping'

    def __init__(self, name, download_config, registry_url, working_dir):
        """
        Initialize the V1Repository.

        :param name:            name of a docker repository
        :type  name:            basestring
        :param download_config: download configuration object
        :type  download_config: nectar.config.DownloaderConfig
        :param registry_url:    URL for the docker registry
        :type  registry_url:    basestring
        :param working_dir:     full path to the directory where files should
                                be saved
        :type  working_dir:     basestring
        """
        self.name = name
        self.download_config = download_config
        self.registry_url = registry_url
        self.listener = AggregatingEventListener()
        self.downloader = HTTPThreadedDownloader(self.download_config, self.listener)
        self.working_dir = working_dir
        self.token = None
        self.endpoint = None

    def _get_single_path(self, path):
        """
        Retrieve a single path within the upstream registry, and return its
        body after deserializing it as json

        :param path:    a full http path to retrieve that will be urljoin'd to the
                        upstream registry url.
        :type  path:    basestring

        :return:    whatever gets deserialized out of the response body's json
        """
        # if talking to docker hub, we'll get an endpoint specified, and then we'll have to get
        # tags from that endpoint instead of talking to the original feed URL.
        if self.endpoint:
            # we assume the same scheme that the registry URL used
            registry_url_parts = urlparse.urlsplit(self.registry_url)
            parts = urlparse.SplitResult(scheme=registry_url_parts.scheme, netloc=self.endpoint,
                                         path=path, query=None, fragment=None)
            url = urlparse.urlunsplit(parts)
        else:
            url = urlparse.urljoin(self.registry_url, path)
        request = DownloadRequest(url, StringIO())
        if path.endswith('/images'):
            # this is required by the docker index and indicates that it should
            # return an auth token
            if request.headers is None:
                request.headers = {}
            request.headers[self.DOCKER_TOKEN_HEADER] = 'true'
        # endpoints require auth
        if self.endpoint:
            self.add_auth_header(request)
        report = self.downloader.download_one(request)

        if report.state == report.DOWNLOAD_FAILED:
            raise IOError(report.error_msg)

        self._parse_response_headers(report.headers)
        return json.loads(report.destination.getvalue())

    def _parse_response_headers(self, headers):
        """
        Some responses can include header information that we need later. This
        grabs those values and stores them for later use.

        :param headers: dictionary-like object where keys are HTTP header names
                        and values are their values.
        :type  headers: dict
        """
        # this is used for authorization on an endpoint
        if self.DOCKER_TOKEN_HEADER in headers:
            self.token = headers[self.DOCKER_TOKEN_HEADER]
        # this tells us what host to use when accessing image files
        if self.DOCKER_ENDPOINT_HEADER in headers:
            self.endpoint = headers[self.DOCKER_ENDPOINT_HEADER]

    def api_version_check(self):
        """
        Make a call to the registry URL's /v1/_ping API call to determine if the registry supports
        API v1.

        :return: True if the v1 API is found, else False
        :rtype:  bool
        """
        _logger.debug('Determining if the registry URL can do v1 of the Docker API.')

        try:
            self._get_single_path(self.API_VERSION_CHECK_PATH)
        except IOError:
            return False

        return True

    def add_auth_header(self, request):
        """
        Given a download request, add an Authorization header if we have an
        auth token available.

        :param request: a download request
        :type  request: nectar.request.DownloadRequest
        """
        if self.token:
            if request.headers is None:
                request.headers = {}
            # this emulates what docker itself does
            request.headers['Authorization'] = 'Token %s' % self.token

    def get_image_ids(self):
        """
        Get a list of all images in the upstream repository. This is
        conceptually a little ambiguous, as there can be images in a repo that
        are neither tagged nor in the ancestry for a tagged image.

        :return:    list of image IDs in the repo
        :rtype:     list
        """
        path = self.IMAGES_PATH % self.name

        _logger.debug('retrieving image ids from remote registry')
        raw_data = self._get_single_path(path)
        return [item['id'] for item in raw_data]

    def get_image_url(self):
        """
        Get a URL for the registry or the endpoint, for use in retrieving image
        files. The "endpoint" is a host name that might be returned in a header
        when retrieving repository data above.

        :return:    a url that is either the provided registry url, or if an
                    endpoint is known, that same url with the host replaced by
                    the endpoint
        :rtype:     basestring
        """
        if self.endpoint:
            parts = list(urlparse.urlsplit(self.registry_url))
            parts[1] = self.endpoint
            return urlparse.urlunsplit(parts)
        else:
            return self.registry_url

    def get_tags(self):
        """
        Get a dictionary of tags from the upstream repo.

        :return:    a dictionary where keys are tag names, and values are either
                    full image IDs or abbreviated image IDs.
        :rtype:     dict
        """
        repo_name = self.name
        # this is a quirk of the docker registry API.
        if '/' not in repo_name:
            repo_name = 'library/' + repo_name

        path = self.TAGS_PATH % repo_name

        _logger.debug('retrieving tags from remote registry')
        raw_data = self._get_single_path(path)
        # raw_data will sometimes be a list of dicts, and sometimes just a dict,
        # depending on what version of the API we're talking to.
        if isinstance(raw_data, list):
            return dict((tag['name'], tag['layer']) for tag in raw_data)
        return raw_data

    def get_ancestry(self, image_ids):
        """
        Retrieve the "ancestry" file for each provided image ID, and save each
        in a directory whose name is the image ID.

        :param image_ids:   list of image IDs for which the ancestry file
                            should be retrieved
        :type  image_ids:   list

        :raises IOError:    if a download fails
        """
        requests = []
        for image_id in image_ids:
            path = self.ANCESTRY_PATH % image_id
            url = urlparse.urljoin(self.get_image_url(), path)
            destination = os.path.join(self.working_dir, image_id, 'ancestry')
            try:
                os.mkdir(os.path.split(destination)[0])
            except OSError, e:
                # it's ok if the directory already exists
                if e.errno != errno.EEXIST:
                    raise
            request = DownloadRequest(url, destination)
            self.add_auth_header(request)
            requests.append(request)

        _logger.debug('retrieving ancestry files from remote registry')
        self.downloader.download(requests)
        if len(self.listener.failed_reports):
            raise IOError(self.listener.failed_reports[0].error_msg)

    def create_download_request(self, image_id, file_name, destination_dir):
        """
        Return a DownloadRequest instance for the given file name and image ID.
        It is desirable to download the actual layer files with a separate
        downloader (for progress tracking, etc), so we just create the download
        requests here and let them get processed elsewhere.

        This adds the Authorization header if a token is known for this
        repository.

        :param image_id:        unique ID of a docker image
        :type  image_id:        basestring
        :param file_name:       name of the file, one of "ancestry", "json",
                                or "layer"
        :type  file_name:       basestring
        :param destination_dir: full path to the directory where file should
                                be saved
        :type  destination_dir: basestring

        :return:    a download request instance
        :rtype:     nectar.request.DownloadRequest
        """
        url = self.get_image_url()
        req = DownloadRequest(urlparse.urljoin(url, '/v1/images/%s/%s' % (image_id, file_name)),
                              os.path.join(destination_dir, file_name))
        self.add_auth_header(req)
        return req


class V2Repository(object):
    """
    This class represents a Docker v2 repository.
    """
    API_VERSION_CHECK_PATH = '/v2/'
    LAYER_PATH = '/v2/{name}/blobs/{digest}'
    MANIFEST_PATH = '/v2/{name}/manifests/{reference}'
    TAGS_PATH = '/v2/{name}/tags/list'

    def __init__(self, name, download_config, registry_url, working_dir):
        """
        Initialize the V2Repository.

        :param name:            name of a docker repository
        :type  name:            basestring
        :param download_config: download configuration object
        :type  download_config: nectar.config.DownloaderConfig
        :param registry_url:    URL for the docker registry
        :type  registry_url:    basestring
        :param working_dir:     full path to the directory where files should
                                be saved
        :type  working_dir:     basestring
        """
        self.name = name
        self.download_config = download_config
        self.registry_url = registry_url
        self.downloader = HTTPThreadedDownloader(self.download_config, AggregatingEventListener())
        self.working_dir = working_dir

    def api_version_check(self):
        """
        Make a call to the registry URL's /v2/ API call to determine if the registry supports API
        v2. If it does not, raise NotImplementedError. If it does, return.

        :return: True if the v2 API is found, else False
        :rtype:  bool
        """
        _logger.debug('Determining if the registry URL can do v2 of the Docker API.')

        try:
            headers, body = self._get_path(self.API_VERSION_CHECK_PATH)
        except IOError:
            return False

        try:
            version = headers['Docker-Distribution-API-Version']
            if version != "registry/2.0":
                return False
            _logger.debug(_('The docker registry is using API version: %(v)s') % {'v': version})
        except KeyError:
            # If the Docker-Distribution-API-Version header isn't present, we will assume that this
            # is a valid Docker 2.0 API server so that simple file-based webservers can serve as our
            # remote feed.
            pass

        return True

    def create_blob_download_request(self, digest, destination_dir):
        """
        Return a DownloadRequest instance for the given blob digest.
        It is desirable to download the blob files with a separate
        downloader (for progress tracking, etc), so we just create the download
        requests here and let them get processed elsewhere.

        :param digest:          digest of the docker blob you wish to download
        :type  digest:          basestring
        :param destination_dir: full path to the directory where file should
                                be saved
        :type  destination_dir: basestring

        :return:    a download request instance
        :rtype:     nectar.request.DownloadRequest
        """
        path = self.LAYER_PATH.format(name=self.name, digest=digest)
        url = urlparse.urljoin(self.registry_url, path)
        req = DownloadRequest(url, os.path.join(destination_dir, digest))
        return req

    def get_manifest(self, reference):
        """
        Get the manifest and its digest for the given reference.

        :param reference: The reference (tag or digest) of the Manifest you wish to retrieve.
        :type  reference: basestring
        :return:          A 2-tuple of the digest and the manifest, both basestrings
        :rtype:           tuple
        """
        path = self.MANIFEST_PATH.format(name=self.name, reference=reference)
        headers, manifest = self._get_path(path)

        digest_header = 'docker-content-digest'
        if digest_header in headers:
            expected_digest = headers[digest_header]
            # The digest is formatted as algorithm:sum, so let's ask our hasher to use the same
            # algorithm as we received in the headers.
            digest = models.Manifest.digest(manifest, expected_digest.split(':')[0])
            if digest != expected_digest:
                msg = _('The Manifest digest does not match the expected value. The remote '
                        'feed announced a digest of {e}, but the downloaded digest was {d}.')
                msg = msg.format(e=expected_digest, d=digest)
                raise IOError(msg)
        else:
            digest = models.Manifest.digest(manifest)
        return digest, manifest

    def get_tags(self):
        """
        Get a list of the available tags in the repository.

        :return: A list of basestrings of the available tags in the repository.
        :rtype:  list
        """
        path = self.TAGS_PATH.format(name=self.name)
        headers, tags = self._get_path(path)
        return json.loads(tags)['tags']

    def _get_path(self, path):
        """
        Retrieve a single path within the upstream registry, and return a 2-tuple of the headers and
        the response body.

        :param path: a full http path to retrieve that will be urljoin'd to the upstream registry
                     url.
        :type  path: basestring

        :return:     (headers, response body)
        :rtype:      tuple
        """
        url = urlparse.urljoin(self.registry_url, path)
        _logger.debug(_('Retrieving {0}'.format(url)))
        request = DownloadRequest(url, StringIO())
        report = self.downloader.download_one(request)

        if report.state == report.DOWNLOAD_FAILED:
            raise IOError(report.error_msg)

        return report.headers, report.destination.getvalue()
