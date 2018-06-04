import mock
import unittest

from pulp_docker.common import dir_transport as transport


class TestVersion(unittest.TestCase):

    def setUp(self):
        self.v00 = transport.Version("0.0")
        self.v10 = transport.Version("1.0")
        self.v11 = transport.Version("1.1")
        self.v199 = transport.Version("1.99")
        self.v20 = transport.Version("2.0")
        self.copy_v11 = transport.Version("1.1")
        self.copy_v00 = transport.Version("0.0")

    def test_read(self):
        """
        Ensure that the file line is correctly parsed.
        """
        mock_version = "Directory Transport Version: 1.1\n"
        with mock.patch('pulp_docker.common.dir_transport.open', create=True) as mopen:
            mock_readline = mopen.return_value.__enter__.return_value.readline
            mock_readline.return_value = mock_version
            version = transport.Version.from_file("path-to-version")

        self.assertEqual(version.version, '1.1')

    def test_read_nonexistant(self):
        try:
            with mock.patch('pulp_docker.common.dir_transport.open', create=True) as mopen:
                mopen.side_effect = IOError
                transport.Version.from_file("path-to-version")
        except IOError:
            pass
        else:
            raise AssertionError("IOError from open should bubble up.")

    def test_eq(self):
        self.assertTrue(self.v11 == self.copy_v11)
        self.assertTrue(self.v00 == self.copy_v00)

        self.assertFalse(self.v10 == self.v11)

    def test_inequality(self):
        self.assertTrue(self.v10 != self.v11)

        self.assertFalse(self.v00 != self.copy_v00)
        self.assertFalse(self.v11 != self.copy_v11)

    def test_gt(self):
        self.assertTrue(self.v11 > self.v10)

        self.assertFalse(self.v10 > self.v11)
        self.assertFalse(self.v11 > self.copy_v11)

    def test_gt_for_large_y_release(self):
        self.assertTrue(self.v20 > self.v199)

    def test_ge(self):
        self.assertTrue(self.v10 >= self.v10)
        self.assertTrue(self.v11 >= self.v10)

        self.assertFalse(self.v10 >= self.v11)

    def test_lt(self):
        self.assertTrue(self.v10 < self.v11)

        self.assertFalse(self.v11 < self.v00)
        self.assertFalse(self.v11 < self.copy_v11)

    def test_lt_for_large_y_release(self):
        self.assertTrue(self.v199 < self.v20)

    def test_le(self):
        self.assertTrue(self.v10 <= self.v10)
        self.assertTrue(self.v10 <= self.v11)

        self.assertFalse(self.v11 <= self.v10)
