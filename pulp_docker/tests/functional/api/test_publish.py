# coding=utf-8
"""Tests that publish docker plugin repositories."""
import unittest
from random import choice

from pulp_smash import api, config
from pulp_smash.pulp3.constants import REPO_PATH
from pulp_smash.pulp3.utils import (
    gen_repo,
    get_content,
    get_versions,
    sync,
)

from pulp_docker.tests.functional.utils import gen_docker_remote
from pulp_docker.tests.functional.constants import (
    DOCKER_CONTENT_NAME,
    DOCKER_REMOTE_PATH,
    DOCKER_PUBLICATION_PATH,
)
from pulp_docker.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class PublishAnyRepoVersionTestCase(unittest.TestCase):
    """Test whether a particular repository version can be published.

    This test targets the following issues:

    * `Pulp #3324 <https://pulp.plan.io/issues/3324>`_
    * `Pulp Smash #897 <https://github.com/PulpQE/pulp-smash/issues/897>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)

    def test_all(self):
        """Test whether a particular repository version can be published.

        1. Create a repository with at least 2 repository versions.
        2. Create a publication by supplying the latest ``repository_version``.
        3. Assert that the publication ``repository_version`` attribute points
           to the latest repository version.
        4. Create a publication by supplying the non-latest ``repository_version``.
        5. Assert that the publication ``repository_version`` attribute points
           to the supplied repository version.
        """
        body = gen_docker_remote()
        remote = self.client.post(DOCKER_REMOTE_PATH, body)
        self.addCleanup(self.client.delete, remote['_href'])

        repo = self.client.post(REPO_PATH, gen_repo())
        self.addCleanup(self.client.delete, repo['_href'])

        sync(self.cfg, remote, repo)

        # Step 1
        repo = self.client.get(repo['_href'])
        for docker_content in get_content(repo)[DOCKER_CONTENT_NAME]:
            self.client.post(
                repo['_versions_href'],
                {'add_content_units': [docker_content['_href']]}
            )
        version_hrefs = tuple(ver['_href'] for ver in get_versions(repo))
        non_latest = choice(version_hrefs[:-1])

        # Step 2
        publication1 = self.client.using_handler(api.task_handler).post(
            DOCKER_PUBLICATION_PATH, {"repository": repo["_href"]})
        # Step 3
        self.assertEqual(publication1['repository_version'], version_hrefs[-1])

        # Step 4
        publication2 = self.client.using_handler(api.task_handler).post(
            DOCKER_PUBLICATION_PATH, {"repository_version": non_latest})

        # Step 5
        self.assertEqual(publication2['repository_version'], non_latest)
