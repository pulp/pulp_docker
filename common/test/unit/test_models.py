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

    def test_relative_path(self):
        image = models.DockerImage('abc', 'xyz', 1024)

        self.assertEqual(image.relative_path, 'docker_image/abc')

    def test_metadata(self):
        image = models.DockerImage('abc', 'xyz', 1024)
        metadata = image.unit_metadata

        self.assertEqual(metadata.get('parent_id'), 'xyz')
        self.assertEqual(metadata.get('size'), 1024)
