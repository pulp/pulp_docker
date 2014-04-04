import unittest

from pulp.plugins.distributor import Distributor

from pulp_docker.common import constants
from pulp_docker.plugins.distributors.distributor import DockerDistributor, entry_point


class TestEntryPoint(unittest.TestCase):
    def test_returns_importer(self):
        distributor, config = entry_point()

        self.assertTrue(issubclass(distributor, Distributor))

    def test_returns_config(self):
        distributor, config = entry_point()

        # make sure it's at least the correct type
        self.assertTrue(isinstance(config, dict))


class TestBasics(unittest.TestCase):
    def test_metadata(self):
        metadata = DockerDistributor.metadata()

        self.assertEqual(metadata['id'], constants.DISTRIBUTOR_TYPE_ID)
        self.assertEqual(metadata['types'], [constants.IMAGE_TYPE_ID])
        self.assertTrue(len(metadata['display_name']) > 0)
