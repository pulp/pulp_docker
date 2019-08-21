# coding=utf-8
"""Tests that recursively add docker content to repositories."""
import unittest

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import gen_repo, sync
from requests.exceptions import HTTPError

from pulp_docker.tests.functional.constants import (
    DOCKER_TAG_PATH,
    DOCKER_TAG_COPY_PATH,
    DOCKER_TAGGING_PATH,
    DOCKER_REMOTE_PATH,
    DOCKER_RECURSIVE_ADD_PATH,
    DOCKERHUB_PULP_FIXTURE_1,
)
from pulp_docker.tests.functional.utils import gen_docker_remote


class TestTagCopy(unittest.TestCase):
    """Test recursive copy of tags content to a repository."""

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
        """Ensure source_repository or source_repository_version is required."""
        with self.assertRaises(HTTPError):
            self.client.post(DOCKER_RECURSIVE_ADD_PATH)

        with self.assertRaises(HTTPError):
            self.client.post(
                DOCKER_RECURSIVE_ADD_PATH,
                {'source_repository': self.from_repo['_href']}
            )

        with self.assertRaises(HTTPError):
            self.client.post(
                DOCKER_RECURSIVE_ADD_PATH,
                {'source_repository_version': self.from_repo['_latest_version_href']}
            )

        with self.assertRaises(HTTPError):
            self.client.post(
                DOCKER_RECURSIVE_ADD_PATH,
                {'destination_repository': self.to_repo['_href']}
            )

    def test_empty_source_repository(self):
        """Ensure exception is raised when source_repository does not have latest version."""
        with self.assertRaises(HTTPError):
            self.client.post(
                DOCKER_TAG_COPY_PATH,
                {
                    # to_repo has no versions.
                    'source_repository': self.to_repo['_href'],
                    'destination_repository': self.from_repo['_href'],
                }
            )

    def test_source_repository_and_source_version(self):
        """Passing source_repository_version and repository returns a 400."""
        with self.assertRaises(HTTPError):
            self.client.post(
                DOCKER_TAG_COPY_PATH,
                {
                    'source_repository': self.from_repo['_href'],
                    'source_repository_version': self.from_repo['_latest_version_href'],
                    'destination_repository': self.to_repo['_href']
                }
            )

    def test_copy_all_tags(self):
        """Passing only source and destination repositories copies all tags."""
        self.client.post(
            DOCKER_TAG_COPY_PATH,
            {
                'source_repository': self.from_repo['_href'],
                'destination_repository': self.to_repo['_href']
            }
        )
        latest_to_repo_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest_from_repo_href = self.client.get(self.from_repo['_href'])['_latest_version_href']
        to_repo_content = self.client.get(latest_to_repo_href)['content_summary']['present']
        from_repo_content = self.client.get(latest_from_repo_href)['content_summary']['present']
        for docker_type in ['docker.tag', 'docker.manifest', 'docker.blob']:
            self.assertEqual(
                to_repo_content[docker_type]['count'],
                from_repo_content[docker_type]['count']
            )

    def test_copy_all_tags_from_version(self):
        """Passing only source version and destination repositories copies all tags."""
        latest_from_repo_href = self.client.get(self.from_repo['_href'])['_latest_version_href']
        self.client.post(
            DOCKER_TAG_COPY_PATH,
            {
                'source_repository_version': latest_from_repo_href,
                'destination_repository': self.to_repo['_href']
            }
        )
        latest_to_repo_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        to_repo_content = self.client.get(latest_to_repo_href)['content_summary']['present']
        from_repo_content = self.client.get(latest_from_repo_href)['content_summary']['present']
        for docker_type in ['docker.tag', 'docker.manifest', 'docker.blob']:
            self.assertEqual(
                to_repo_content[docker_type]['count'],
                from_repo_content[docker_type]['count']
            )

    def test_copy_tags_by_name(self):
        """Passing only source and destination repositories copies all tags."""
        self.client.post(
            DOCKER_TAG_COPY_PATH,
            {
                'source_repository': self.from_repo['_href'],
                'destination_repository': self.to_repo['_href'],
                'names': ['ml_i', 'manifest_c']
            }
        )
        latest_to_repo_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        to_repo_content = self.client.get(latest_to_repo_href)['content_summary']['present']
        self.assertEqual(to_repo_content['docker.tag']['count'], 2)
        # ml_i has 1 manifest list, 2 manifests, manifest_c has 1 manifest
        self.assertEqual(to_repo_content['docker.manifest']['count'], 4)
        # each manifest (not manifest list) has 2 blobs
        self.assertEqual(to_repo_content['docker.blob']['count'], 6)

    def test_copy_tags_by_name_empty_list(self):
        """Passing only source and destination repositories copies all tags."""
        self.client.post(
            DOCKER_TAG_COPY_PATH,
            {
                'source_repository': self.from_repo['_href'],
                'destination_repository': self.to_repo['_href'],
                'names': []
            }
        )
        latest_to_repo_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        # A new version was created
        self.assertNotEqual(latest_to_repo_href, self.to_repo['_latest_version_href'])

        to_repo_content = self.client.get(latest_to_repo_href)['content_summary']['present']
        # No content added
        for docker_type in ['docker.tag', 'docker.manifest', 'docker.blob']:
            self.assertFalse(docker_type in to_repo_content)

    def test_copy_tags_with_conflicting_names(self):
        """If tag names are already present in a repository, the conflicting tags are removed."""
        self.client.post(
            DOCKER_TAG_COPY_PATH,
            {
                'source_repository': self.from_repo['_href'],
                'destination_repository': self.to_repo['_href']
            }
        )
        # Same call
        self.client.post(
            DOCKER_TAG_COPY_PATH,
            {
                'source_repository': self.from_repo['_href'],
                'destination_repository': self.to_repo['_href']
            }
        )
        latest_to_repo_href = self.client.get(self.to_repo['_href'])['_latest_version_href']
        latest_from_repo_href = self.client.get(self.from_repo['_href'])['_latest_version_href']
        to_repo_content = self.client.get(latest_to_repo_href)['content_summary']
        from_repo_content = self.client.get(latest_from_repo_href)['content_summary']
        for docker_type in ['docker.tag', 'docker.manifest', 'docker.blob']:
            self.assertEqual(
                to_repo_content['present'][docker_type]['count'],
                from_repo_content['present'][docker_type]['count']
            )

        self.assertEqual(
            to_repo_content['added']['docker.tag']['count'],
            from_repo_content['present']['docker.tag']['count']
        )
        self.assertEqual(
            to_repo_content['removed']['docker.tag']['count'],
            from_repo_content['present']['docker.tag']['count']
        )


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
