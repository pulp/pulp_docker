from cStringIO import StringIO
import json
import logging
import urllib
import urlparse

from nectar.request import DownloadRequest


_logger = logging.getLogger(__name__)


def add_auth_header(request, token):
    """
    Adds the token into the request's headers as specified in the Docker v2 API documentation.

    https://docs.docker.com/registry/spec/auth/token/#using-the-bearer-token

    :param request: a download request
    :type  request: nectar.request.DownloadRequest
    :param token: a Bearer token to be inserted into the Authorization header
    :type  token: basestring
    """
    if request.headers is None:
        request.headers = {}
    request.headers['Authorization'] = 'Bearer %s' % token


def request_token(downloader, request, response_headers):
    """
    Attempts to retrieve the correct token based on the 401 response header.

    According to the Docker API v2 documentation, the token be retrieved by issuing a GET
    request to the url specified by the `realm` within the `WWW-Authenticate` header. This
    request should add the following query parameters:

        service: the name of the service that hosts the desired resource
        scope:   the specific resource and permissions requested

    https://docs.docker.com/registry/spec/auth/token/#requesting-a-token

    :param downloader: Nectar downloader that will be used to issue a download request
    :type  downloader: nectar.downloaders.threaded.HTTPThreadedDownloader
    :param request: a download request
    :type  request: nectar.request.DownloadRequest
    :param response_headers: headers from the 401 response
    :type  response_headers: basestring
    :return: Bearer token for requested resource
    :rtype:  str
    """
    auth_info = parse_401_response_headers(response_headers)
    try:
        token_url = auth_info.pop('realm')
    except KeyError:
        raise IOError("No realm specified for token auth challenge.")

    parse_result = urlparse.urlparse(token_url)
    query_dict = urlparse.parse_qs(parse_result.query)
    query_dict.update(auth_info)
    url_pieces = list(parse_result)
    url_pieces[4] = urllib.urlencode(query_dict)
    token_url = urlparse.urlunparse(url_pieces)

    token_data = StringIO()
    token_request = DownloadRequest(token_url, token_data)
    _logger.debug("Requesting token from {url}".format(url=token_url))
    report = downloader.download_one(token_request)
    if report.state == report.DOWNLOAD_FAILED:
        raise IOError(report.error_msg)

    return json.loads(token_data.getvalue())['token']


def parse_401_response_headers(response_headers):
    """
    Parse the headers from a 401 response into a dictionary that contains the information
    necessary to retrieve a token.

    :param response_headers: headers returned in a 401 response
    :type  response_headers: requests.structures.CaseInsensitiveDict
    """
    auth_header = response_headers.get('www-authenticate')
    if auth_header is None:
        raise IOError("401 responses are expected to conatin authentication information")
    auth_header = auth_header[len("Bearer "):]

    # The remaining string consists of comma seperated key=value pairs
    auth_dict = {}
    for key, value in (item.split('=') for item in auth_header.split(',')):
        # The value is a string within a string, ex: '"value"'
        auth_dict[key] = json.loads(value)
    return auth_dict
