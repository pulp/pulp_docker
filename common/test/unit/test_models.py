import unittest

from pulp_docker.common import models


class TestBasics(unittest.TestCase):
    def test_init_info(self):
        image = models.DockerImage('abc', 'xyz', 1024)

        self.assertEqual(image.image_id, 'abc')
        self.assertEqual(image.parent_id, 'xyz')
        self.assertEqual(image.size, 1024)

    def test_unit_key(self):
        image = models.DockerImage('abc', 'xyz', 1024)

        self.assertEqual(image.unit_key, {'image_id': 'abc'})
