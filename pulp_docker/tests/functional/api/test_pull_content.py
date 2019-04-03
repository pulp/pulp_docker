# coding=utf-8
"""Tests that verify that images served by Pulp can be pulled."""
import contextlib
import unittest
from urllib.parse import urljoin

from pulp_smash import api, cli, config, exceptions
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import (
    get_content,
    gen_distribution,
    gen_publisher,
    gen_repo,
    publish,
    sync,
)

from pulp_docker.tests.functional.utils import (
    gen_docker_remote,
    get_docker_hub_remote_blobsums
)

from pulp_docker.tests.functional.constants import (
    DOCKER_CONTENT_NAME,
    DOCKER_DISTRIBUTION_PATH,
    DOCKER_REMOTE_PATH,
    DOCKER_PUBLISHER_PATH,
    DOCKER_UPSTREAM_NAME,
    DOCKER_UPSTREAM_TAG,
)
from pulp_docker.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class PullContentTestCase(unittest.TestCase):
    """Verify whether images served by Pulp can be pulled."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables.

        1. Create a repository.
        2. Create a remote pointing to external registry.
        3. Sync the repository using the remote and re-read the repo data.
        4. Create a docker publisher.
        5. Use the publisher to create a publication.
        6. Create a docker distribution to serve the publication.

        This tests targets the following issue:

        * `Pulp #4460 <https://pulp.plan.io/issues/4460>`_
        """
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.page_handler)
        cls.teardown_cleanups = []

        with contextlib.ExitStack() as stack:
            # ensure tearDownClass runs if an error occurs here
            stack.callback(cls.tearDownClass)

            # Step 1
            _repo = cls.client.post(REPO_PATH, gen_repo())
            cls.teardown_cleanups.append((cls.client.delete, _repo['_href']))

            # Step 2
            cls.remote = cls.client.post(
                DOCKER_REMOTE_PATH, gen_docker_remote()
            )
            cls.teardown_cleanups.append(
                (cls.client.delete, cls.remote['_href'])
            )

            # Step 3
            sync(cls.cfg, cls.remote, _repo)
            cls.repo = cls.client.get(_repo['_href'])

            # Step 4
            cls.publisher = cls.client.post(
                DOCKER_PUBLISHER_PATH, gen_publisher()
            )
            cls.teardown_cleanups.append(
                (cls.client.delete, cls.publisher['_href'])
            )

            # Step 5.
            cls.publication = publish(cls.cfg, cls.publisher, cls.repo)
            cls.teardown_cleanups.append(
                (cls.client.delete, cls.publication['_href'])
            )

            # Step 6.
            response_dict = cls.client.post(
                DOCKER_DISTRIBUTION_PATH,
                gen_distribution(publication=cls.publication['_href'])
            )
            dist_task = cls.client.get(response_dict['task'])
            distribution_href = dist_task['created_resources'][0]
            cls.distribution = cls.client.get(distribution_href)
            cls.teardown_cleanups.append(
                (cls.client.delete, cls.distribution['_href'])
            )

            # remove callback if everything goes well
            stack.pop_all()

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        for cleanup_function, args in reversed(cls.teardown_cleanups):
            cleanup_function(args)

    def test_api_returns_same_checksum(self):
        """Verify that pulp serves image with the same checksum of remote.

        1. Call pulp repository API and get the content_summary for repo.
        2. Call dockerhub API and get blobsums for synced image.
        3. Compare the checksums.
        """
        # Get local checksums for content synced from remote registy
        checksums = [
            content['digest'] for content
            in get_content(self.repo)[DOCKER_CONTENT_NAME]
        ]

        # Assert that at least one layer is synced from remote:latest
        # and the checksum matched with remote
        self.assertTrue(
            any(
                [
                    result['blobSum'] in checksums
                    for result in get_docker_hub_remote_blobsums()
                ]
            ),
            'Cannot find a matching layer on remote registry.'
        )

    def test_pull_image(self):
        """Verify that a client can pull the image from Pulp.

        1. Using the RegistryClient pull the image from Pulp.
        2. Pull the same image from remote registry.
        3. Verify both images has the same checksum.
        4. Ensure image is deleted after the test.
        """
        registry = cli.RegistryClient(self.cfg)
        registry.raise_if_unsupported(
            unittest.SkipTest, 'Test requires podman/docker'
        )

        local_url = urljoin(
            self.cfg.get_content_host_base_url(),
            self.distribution['base_path']
        )

        registry.pull(local_url)
        self.teardown_cleanups.append((registry.rmi, local_url))
        local_image = registry.inspect(local_url)

        registry.pull(DOCKER_UPSTREAM_NAME)
        self.teardown_cleanups.append((registry.rmi, DOCKER_UPSTREAM_NAME))
        remote_image = registry.inspect(DOCKER_UPSTREAM_NAME)

        self.assertEqual(
            local_image[0]['Digest'],
            remote_image[0]['Digest']
        )

    def test_pull_image_with_tag(self):
        """Verify that a client can pull the image from Pulp with a tag.

        1. Using the RegistryClient pull the image from Pulp specifying a tag.
        2. Pull the same image and same tag from remote registry.
        3. Verify both images has the same checksum.
        4. Ensure image is deleted after the test.
        """
        registry = cli.RegistryClient(self.cfg)
        registry.raise_if_unsupported(
            unittest.SkipTest, 'Test requires podman/docker'
        )

        local_url = urljoin(
            self.cfg.get_content_host_base_url(),
            self.distribution['base_path']
        ) + DOCKER_UPSTREAM_TAG

        registry.pull(local_url)
        self.teardown_cleanups.append((registry.rmi, local_url))
        local_image = registry.inspect(local_url)

        registry.pull(DOCKER_UPSTREAM_NAME + DOCKER_UPSTREAM_TAG)
        self.teardown_cleanups.append(
            (registry.rmi, DOCKER_UPSTREAM_NAME + DOCKER_UPSTREAM_TAG)
        )
        remote_image = registry.inspect(
            DOCKER_UPSTREAM_NAME + DOCKER_UPSTREAM_TAG
        )

        self.assertEqual(
            local_image[0]['Digest'],
            remote_image[0]['Digest']
        )

    def test_pull_inexistent_image(self):
        """Verify that a client cannot pull inexistent image from Pulp.

        1. Using the RegistryClient try to pull inexistent image from Pulp.
        2. Assert that error is occured and nothing has been pulled.
        """
        registry = cli.RegistryClient(self.cfg)
        registry.raise_if_unsupported(
            unittest.SkipTest, 'Test requires podman/docker'
        )

        local_url = urljoin(
            self.cfg.get_content_host_base_url(),
            "inexistentimagename"
        )
        with self.assertRaises(exceptions.CalledProcessError):
            registry.pull(local_url)
