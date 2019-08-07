# coding=utf-8
"""Tests that recursively add docker content to repositories."""
import unittest

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo, sync
from requests.exceptions import HTTPError

from pulp_docker.tests.functional.constants import (
    DOCKER_TAG_PATH,
    DOCKER_TAGGING_PATH,
    DOCKER_REMOTE_PATH,
    DOCKER_RECURSIVE_ADD_PATH,
    DOCKERHUB_PULP_FIXTURE_1,
)
from pulp_docker.tests.functional.utils import gen_docker_remote


class TestRecursiveAdd(unittest.TestCase):
    """Test recursively adding docker content to a repository."""

    @classmethod
    def setUpClass(cls):
        """Sync pulp/test-fixture-1 so we can copy content from it."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)
        cls.from_repo = cls.client.post(REPO_PATH, gen_repo())
        remote_data = gen_docker_remote(upstream_name=DOCKERHUB_PULP_FIXTURE_1)
        cls.remote = cls.client.post(DOCKER_REMOTE_PATH, remote_data)
        sync(cls.cfg, cls.remote, cls.from_repo)
        latest_version = cls.client.get(cls.from_repo['_href'])['_latest_version_href']
        cls.latest_from_version = "repository_version={version}".format(version=latest_version)

    def setUp(self):
        """Create an empty repository to copy into."""
        self.to_repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, self.to_repo['_href'])

    @classmethod
    def tearDownClass(cls):
        """Delete things made in setUpClass. addCleanup feature does not work with setupClass."""
        cls.client.delete(cls.from_repo['_href'])
        cls.client.delete(cls.remote['_href'])

    def test_missing_repository_argument(self):
        """Ensure Repository argument is required."""
        with self.assertRaises(HTTPError):
            self.client.post(DOCKER_RECURSIVE_ADD_PATH)

    def test_repository_only(self):
        """Passing only a repository creates a new version."""
        self.client.post(DOCKER_RECURSIVE_ADD_PATH, {'repository': self.to_repo['_href']})
        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        self.assertNotEqual(latest_version_href, self.to_repo['_latest_version_href'])

    def test_manifest_recursion(self):
        """Add a manifest and its related blobs."""
        manifest_a = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=manifest_a&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['tagged_manifest']
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {'repository': self.to_repo['_href'], 'content_units': [manifest_a]})
        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest = self.client.get(latest_version_href)

        # No tags added
        self.assertFalse('docker.manifest-tag' in latest['content_summary']['added'])

        # manifest a has 2 blobs
        self.assertEqual(latest['content_summary']['added']['docker.manifest']['count'], 1)
        self.assertEqual(latest['content_summary']['added']['docker.blob']['count'], 2)

    def test_manifest_list_recursion(self):
        """Add a Manifest List, related manifests, and related blobs."""
        ml_i = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=ml_i&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['tagged_manifest']
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {'repository': self.to_repo['_href'], 'content_units': [ml_i]})
        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest = self.client.get(latest_version_href)

        # No tags added
        self.assertFalse('docker.tag' in latest['content_summary']['added'])
        # 1 manifest list 2 manifests
        self.assertEqual(latest['content_summary']['added']['docker.manifest']['count'], 3)

    def test_tagged_manifest_list_recursion(self):
        """Add a tagged manifest list, and its related manifests and blobs."""
        ml_i_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=ml_i&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {'repository': self.to_repo['_href'], 'content_units': [ml_i_tag]})
        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest = self.client.get(latest_version_href)
        self.assertEqual(latest['content_summary']['added']['docker.tag']['count'], 1)
        # 1 manifest list 2 manifests
        self.assertEqual(latest['content_summary']['added']['docker.manifest']['count'], 3)
        self.assertEqual(latest['content_summary']['added']['docker.blob']['count'], 4)

    def test_tagged_manifest_recursion(self):
        """Add a tagged manifest and its related blobs."""
        manifest_a_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=manifest_a&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {'repository': self.to_repo['_href'], 'content_units': [manifest_a_tag]})
        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest = self.client.get(latest_version_href)

        self.assertEqual(latest['content_summary']['added']['docker.tag']['count'], 1)
        self.assertEqual(latest['content_summary']['added']['docker.manifest']['count'], 1)
        self.assertEqual(latest['content_summary']['added']['docker.blob']['count'], 2)

    def test_tag_replacement(self):
        """Add a tagged manifest to a repo with a tag of that name already in place."""
        manifest_a_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=manifest_a&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']

        # Add manifest_b to the repo
        manifest_b = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=manifest_b&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['tagged_manifest']
        manifest_b_digest = self.client.get(manifest_b)['digest']
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {'repository': self.to_repo['_href'], 'content_units': [manifest_b]})
        # Tag manifest_b as `manifest_a`
        params = {
            'tag': "manifest_a",
            'repository': self.to_repo['_href'],
            'digest': manifest_b_digest
        }
        self.client.post(DOCKER_TAGGING_PATH, params)

        # Now add original manifest_a tag to the repo, which should remove the
        # new manifest_a tag, but leave the tagged manifest (manifest_b)
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {'repository': self.to_repo['_href'], 'content_units': [manifest_a_tag]})

        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest = self.client.get(latest_version_href)
        self.assertEqual(latest['content_summary']['added']['docker.tag']['count'], 1)
        self.assertEqual(latest['content_summary']['removed']['docker.tag']['count'], 1)
        self.assertFalse('docker.manifest' in latest['content_summary']['removed'])
        self.assertFalse('docker.blob' in latest['content_summary']['removed'])

    def test_many_tagged_manifest_lists(self):
        """Add several Manifest List, related manifests, and related blobs."""
        ml_i_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=ml_i&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']
        ml_ii_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=ml_ii&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']
        ml_iii_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=ml_iii&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']
        ml_iv_tag = self.client.get("{unit_path}?{filters}".format(
            unit_path=DOCKER_TAG_PATH,
            filters="name=ml_iv&{v_filter}".format(v_filter=self.latest_from_version),
        ))['results'][0]['_href']
        self.client.post(
            DOCKER_RECURSIVE_ADD_PATH,
            {
                'repository': self.to_repo['_href'],
                'content_units': [ml_i_tag, ml_ii_tag, ml_iii_tag, ml_iv_tag]
            }
        )
        latest_version_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest = self.client.get(latest_version_href)

        self.assertEqual(latest['content_summary']['added']['docker.tag']['count'], 4)
        self.assertEqual(latest['content_summary']['added']['docker.manifest']['count'], 9)
        self.assertEqual(latest['content_summary']['added']['docker.blob']['count'], 10)
