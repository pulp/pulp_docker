# coding=utf-8
"""Tests for tagging and untagging images."""
import unittest

from pulp_smash import api, config
from pulp_smash.pulp3.utils import gen_repo, sync
from pulp_smash.pulp3.constants import REPO_PATH

from pulp_docker.tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from pulp_docker.tests.functional.utils import gen_docker_remote

from pulp_docker.tests.functional.constants import (
    DOCKER_TAG_PATH,
    DOCKER_TAGGING_PATH,
    DOCKER_REMOTE_PATH,
    DOCKERHUB_PULP_FIXTURE_1,
    DOCKER_UNTAGGING_PATH
)
from requests import HTTPError


class TaggingTestCase(unittest.TestCase):
    """Test case for tagging and untagging images."""

    @classmethod
    def setUpClass(cls):
        """Create class wide-variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

        cls.repository = cls.client.post(REPO_PATH, gen_repo())
        remote_data = gen_docker_remote(upstream_name=DOCKERHUB_PULP_FIXTURE_1)
        cls.remote = cls.client.post(DOCKER_REMOTE_PATH, remote_data)
        sync(cls.cfg, cls.remote, cls.repository)

    @classmethod
    def tearDownClass(cls):
        """Clean generated resources."""
        cls.client.delete(cls.repository['_href'])
        cls.client.delete(cls.remote['_href'])

    def test_01_tag_first_image(self):
        """
        Create a new test for manifest.

        This test checks if the tag was created in a new repository version.
        """
        manifest_a = self.get_manifest_by_tag('manifest_a')
        response = self.tag_image(manifest_a, 'new_tag')

        new_repository_version_href = '{repository_href}versions/{new_version}/'.format(
            repository_href=self.repository['_href'],
            new_version='2'
        )

        created_tag = self.client.get('{unit_path}?{filters}'.format(
            unit_path=DOCKER_TAG_PATH,
            filters=f'repository_version_added={new_repository_version_href}'
        ))['results'][0]
        self.assertEqual(created_tag['name'], 'new_tag', created_tag['name'])

        self.assertEqual(
            set(response['created_resources']),
            {new_repository_version_href, created_tag['_href']},
            set(response['created_resources'])
        )

    def test_02_tag_first_image_with_same_tag(self):
        """
        Tag the same manifest with the same name.

        This test checks if a new repository version was created with no content added.
        """
        manifest_a = self.get_manifest_by_tag('manifest_a')
        response = self.tag_image(manifest_a, 'new_tag')

        new_repository_version_href = '{repository_href}versions/{new_version}/'.format(
            repository_href=self.repository['_href'],
            new_version='3'
        )

        repository_version = self.client.get(new_repository_version_href)
        added_content = repository_version['content_summary']['added']
        self.assertEqual(added_content, {}, added_content)

        self.assertEqual(
            set(response['created_resources']),
            {new_repository_version_href},
            set(response['created_resources'])
        )

    def test_03_tag_second_image_with_same_tag(self):
        """
        Tag a different manifest with the same name.

        This test checks if a new repository version was created with a new content added
        and the old removed.
        """
        manifest_a = self.get_manifest_by_tag('manifest_a')
        manifest_b = self.get_manifest_by_tag('manifest_b')
        response = self.tag_image(manifest_b, 'new_tag')

        new_repository_version_href = '{repository_href}versions/{new_version}/'.format(
            repository_href=self.repository['_href'],
            new_version='4'
        )
        created_tag = self.client.get('{unit_path}?{filters}'.format(
            unit_path=DOCKER_TAG_PATH,
            filters=f'repository_version_added={new_repository_version_href}'
        ))['results'][0]
        self.assertEqual(created_tag['name'], 'new_tag', created_tag['name'])

        created_tag_manifest = self.client.get(created_tag['tagged_manifest'])
        self.assertEqual(created_tag_manifest, manifest_b, created_tag_manifest)

        deleted_tag = self.client.get('{unit_path}?{filters}'.format(
            unit_path=DOCKER_TAG_PATH,
            filters=f'repository_version_removed={new_repository_version_href}'
        ))['results'][0]
        self.assertEqual(deleted_tag['name'], 'new_tag', deleted_tag['name'])

        deleted_tag_manifest = self.client.get(deleted_tag['tagged_manifest'])
        self.assertEqual(deleted_tag_manifest, manifest_a, deleted_tag_manifest)

        self.assertEqual(
            set(response['created_resources']),
            {new_repository_version_href, created_tag['_href']},
            set(response['created_resources'])
        )

    def test_04_untag_second_image(self):
        """Untag the manifest and check if the tag was added in a new repository version."""
        response = self.untag_image('new_tag')

        new_repository_version_href = '{repository_href}versions/{new_version}/'.format(
            repository_href=self.repository['_href'],
            new_version='5'
        )

        deleted_tags_href = '{unit_path}?{filters}'.format(
            unit_path=DOCKER_TAG_PATH,
            filters=f'repository_version_removed={new_repository_version_href}'
        )

        repository_version = self.client.get(new_repository_version_href)
        removed_content = repository_version['content_summary']['removed']
        removed_tags = removed_content['docker.tag']['href']
        self.assertEqual(removed_tags, deleted_tags_href, removed_tags)

        deleted_tag = self.client.get(deleted_tags_href)['results'][0]
        self.assertEqual(deleted_tag['name'], 'new_tag', deleted_tag)

        self.assertEqual(
            response['created_resources'],
            [new_repository_version_href],
            response['created_resources']
        )

    def test_05_untag_second_image_again(self):
        """Untag the manifest that was already untagged."""
        with self.assertRaises(HTTPError):
            self.untag_image('new_tag')

    def get_manifest_by_tag(self, tag_name):
        """Fetch a manifest by the tag name."""
        latest_version = self.client.get(
            self.repository['_href']
        )['_latest_version_href']

        manifest_a_href = self.client.get('{unit_path}?{filters}'.format(
            unit_path=DOCKER_TAG_PATH,
            filters=f'name={tag_name}&repository_version={latest_version}'
        ))['results'][0]['tagged_manifest']
        return self.client.get(manifest_a_href)

    def tag_image(self, manifest, tag_name):
        """Perform a tagging operation."""
        params = {
            'tag': tag_name,
            'repository': self.repository['_href'],
            'digest': manifest['digest']
        }
        response = self.client.post(DOCKER_TAGGING_PATH, params)
        return self.client.get(response['task'])

    def untag_image(self, tag_name):
        """Perform an untagging operation."""
        params = {
            'tag': tag_name,
            'repository': self.repository['_href']
        }
        response = self.client.post(DOCKER_UNTAGGING_PATH, params)
        return self.client.get(response['task'])
