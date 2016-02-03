from pulp.common.compat import unittest
import mock

from pulp_docker.plugins import token_util


class TestAddAuthHeader(unittest.TestCase):
    """
    Tests for adding a bearer token to a request header.
    """

    def test_no_headers(self):
        """
        Test that when there are no existing headers, it is added.
        """
        mock_req = mock.MagicMock()
        mock_req.headers = None

        token_util.add_auth_header(mock_req, "mock token")
        self.assertDictEqual(mock_req.headers, {"Authorization": "Bearer mock token"})

    def test_with_headers(self):
        """
        Test that when the headers exists, the auth token is added to it.
        """
        mock_req = mock.MagicMock()
        mock_req.headers = {"mock": "header"}

        token_util.add_auth_header(mock_req, "mock token")
        self.assertDictEqual(mock_req.headers, {"Authorization": "Bearer mock token",
                                                "mock": "header"})


class TestRequestToken(unittest.TestCase):
    """
    Tests for the utility to request a token from the response headers of a 401.
    """
    @mock.patch('pulp_docker.plugins.token_util.parse_401_response_headers')
    def test_no_realm(self, mock_parse):
        """
        When the realm is not specified, raise.
        """
        m_downloader = mock.MagicMock()
        m_req = mock.MagicMock()
        m_headers = mock.MagicMock()
        resp_headers = {'missing': 'realm'}
        mock_parse.return_value = resp_headers
        self.assertRaises(IOError, token_util.request_token, m_downloader, m_req, m_headers)
        mock_parse.assert_called_once_with(m_headers)

    @mock.patch('pulp_docker.plugins.token_util.StringIO')
    @mock.patch('pulp_docker.plugins.token_util.DownloadRequest')
    @mock.patch('pulp_docker.plugins.token_util.urllib.urlencode')
    @mock.patch('pulp_docker.plugins.token_util.parse_401_response_headers')
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
        token_util.request_token(m_downloader, m_req, m_headers)

        mock_encode.assert_called_once_with({'other_info': 'stuff'})
        m_dl_req.assert_called_once_with('url?other_info=stuff', m_string_io.return_value)
        mock_parse.assert_called_once_with(m_headers)
        m_downloader.download_one.assert_called_once_with(m_dl_req.return_value)


class TestParse401ResponseHeaders(unittest.TestCase):
    """
    Tests for parsing 401 headers.
    """

    def test_missing_header(self):
        """
        Raise if 401 does not include the header with authentication information.
        """
        headers = {'missing-www-auth': 'should fail'}
        self.assertRaises(IOError, token_util.parse_401_response_headers, headers)

    def test_dict_created(self):
        """
        Ensure that the www-authenticate header is correctly parsed into a dict.
        """
        headers = {'www-authenticate':
                   'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'}
        ret = token_util.parse_401_response_headers(headers)
        self.assertDictEqual(ret, {"realm": "https://auth.docker.io/token",
                                   "service": "registry.docker.io"})
