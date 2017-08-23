from pulp.common.compat import unittest
import mock

from pulp_docker.plugins import auth_util


class TestUpdateAuthHeader(unittest.TestCase):
    """
    Tests for adding a bearer token to a request header.
    """

    def test_no_headers(self):
        """
        Test that when there are no existing headers, it is added.
        """
        mock_headers = auth_util.update_token_auth_header(None, "mock token")
        self.assertDictEqual(mock_headers, {"Authorization": "Bearer mock token"})

    def test_with_headers(self):
        """
        Test that when the headers exists, the auth token is added to it.
        """
        updated = auth_util.update_token_auth_header({"mock": "header"}, "mock token")
        self.assertDictEqual(updated, {"Authorization": "Bearer mock token", "mock": "header"})


class TestUpdateBasicAuthHeader(unittest.TestCase):
    """
    Tests for adding a basicauth header to a request header.
    """

    def test_no_headers(self):
        """
        Test that when there are no existing headers, it is added.
        """
        mock_headers = auth_util.update_basic_auth_header(None, "user", "pass")
        self.assertDictEqual(mock_headers, {"Authorization": "Basic dXNlcjpwYXNz"})

    def test_with_headers(self):
        """
        Test that when the headers exists, the auth token is added to it.
        """
        updated = auth_util.update_basic_auth_header({"mock": "header"}, "user", "pass")
        self.assertDictEqual(updated, {"Authorization": "Basic dXNlcjpwYXNz", "mock": "header"})


class TestRequestToken(unittest.TestCase):
    """
    Tests for the utility to request a token from the response headers of a 401.
    """
    @mock.patch('pulp_docker.plugins.auth_util.parse_401_token_response_headers')
    def test_no_realm(self, mock_parse):
        """
        When the realm is not specified, raise.
        """
        m_downloader = mock.MagicMock()
        m_req = mock.MagicMock()
        m_headers = mock.MagicMock()
        resp_headers = {'missing': 'realm'}
        mock_parse.return_value = resp_headers
        self.assertRaises(IOError, auth_util.request_token, m_downloader, m_req, m_headers)
        mock_parse.assert_called_once_with(m_headers)

    @mock.patch('pulp_docker.plugins.auth_util.StringIO')
    @mock.patch('pulp_docker.plugins.auth_util.DownloadRequest')
    @mock.patch('pulp_docker.plugins.auth_util.urllib.urlencode')
    @mock.patch('pulp_docker.plugins.auth_util.parse_401_token_response_headers')
    def test_as_expected(self, mock_parse, mock_encode, m_dl_req, m_string_io):
        """
        Test that a request is created with correct query parameters to retrieve a bearer token.
        """
        m_downloader = mock.MagicMock()
        m_req = mock.MagicMock()
        m_headers = mock.MagicMock()
        m_string_io.return_value.getvalue.return_value = '{"token": "Hey, its a token!"}'
        mock_parse.return_value = {'realm': 'url', 'other_info': 'stuff'}
        mock_encode.return_value = 'other_info=stuff'
        auth_util.request_token(m_downloader, m_req, m_headers)

        mock_encode.assert_called_once_with({'other_info': 'stuff'})
        m_dl_req.assert_called_once_with('url?other_info=stuff', m_string_io.return_value)
        mock_parse.assert_called_once_with(m_headers)
        m_downloader.download_one.assert_called_once_with(m_dl_req.return_value)


class TestParse401TokenResponseHeaders(unittest.TestCase):
    """
    Tests for parsing 401 headers.
    """

    def test_dict_created(self):
        """
        Ensure that the www-authenticate header is correctly parsed into a dict.
        """
        auth_header = 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'
        ret = auth_util.parse_401_token_response_headers(auth_header)
        self.assertDictEqual(ret, {"realm": "https://auth.docker.io/token",
                                   "service": "registry.docker.io"})

    def test_multiple_resource_actions(self):
        """
        Ensure that the www-authenticate header is correctly parsed into a dict
        when there are multiple resource actions specified.
        """
        auth_header = 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io",' \
                      'some=1,scope="repository:samalba/my-app:pull,push",foo="bar",answer=42'
        ret = auth_util.parse_401_token_response_headers(auth_header)
        self.assertDictEqual(ret, {"realm": "https://auth.docker.io/token",
                                   "service": "registry.docker.io",
                                   "answer": 42,
                                   "foo": "bar",
                                   "scope": "repository:samalba/my-app:pull,push",
                                   "some": 1})
