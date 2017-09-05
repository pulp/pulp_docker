from cStringIO import StringIO
import base64
import json
import logging
import re
import urllib
import urlparse

from nectar.request import DownloadRequest


_logger = logging.getLogger(__name__)


def update_token_auth_header(headers, token):
    """
    Adds the token into the request's headers as specified in the Docker v2 API documentation.

    https://docs.docker.com/registry/spec/auth/token/#using-the-bearer-token

    :param headers: headers for a request or session
    :type  headers: dict or None
    :param token: a Bearer token to be inserted into the Authorization header
    :type  token: basestring
    """
    headers = headers or {}
    headers['Authorization'] = 'Bearer %s' % token
    return headers


def update_basic_auth_header(headers, username, password):
    """
    Adds basic auth into the request's headers

    :param headers: headers for a request or session
    :type  headers: dict or None
    :param username: username inserted into the Authorization header
    :type  token: basestring
    :param password: password inserted into the Authorization header
    :type  token: basestring
    :return: header with updated authorization information
    :rtype:  header: dict
    """
    headers = headers or {}
    headers['Authorization'] = 'Basic {}'.format(base64.b64encode(username + ':' + password))
    return headers


def request_token(downloader, request, auth_header):
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
    :param auth_header: www-authenticate header returned in a 401 response
    :type  auth_header: basestring
    :return: Bearer token for requested resource
    :rtype:  str
    """
    auth_info = parse_401_token_response_headers(auth_header)
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
    downloader.session.headers.pop('Authorization', None)
    report = downloader.download_one(token_request)
    if report.state == report.DOWNLOAD_FAILED:
        raise IOError(report.error_msg)

    return json.loads(token_data.getvalue())['token']


def parse_401_token_response_headers(auth_header):
    """
    Parse the www-authenticate header from a 401 response into a dictionary that contains
    the information necessary to retrieve a token.

    :param auth_header: www-authenticate header returned in a 401 response
    :type  auth_header: basestring
    """
    auth_header = auth_header[len("Bearer "):]
    auth_header = re.split(',(?=[^=,]+=)', auth_header)

    # The remaining string consists of comma seperated key=value pairs
    auth_dict = {}
    for key, value in (item.split('=') for item in auth_header):
        # The value is a string within a string, ex: '"value"'
        auth_dict[key] = json.loads(value)
    return auth_dict
