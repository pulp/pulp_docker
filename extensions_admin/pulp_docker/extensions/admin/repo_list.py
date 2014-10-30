from gettext import gettext as _

from pulp.client.commands.repo.cudl import ListRepositoriesCommand
from pulp.common import constants as pulp_constants

from pulp_docker.common import constants


class ListDockerRepositoriesCommand(ListRepositoriesCommand):

    def __init__(self, context):
        repos_title = _('Docker Repositories')
        super(ListDockerRepositoriesCommand, self).__init__(context, repos_title=repos_title)

        # Both get_repositories and get_other_repositories will act on the full
        # list of repositories. Lazy cache the data here since both will be
        # called in succession, saving the round trip to the server.
        self.all_repos_cache = None

    def get_repositories(self, query_params, **kwargs):
        """
        Get a list of all the docker repositories that match the specified query params

        :param query_params: query parameters for refining the list of repositories
        :type query_params: dict
        :param kwargs: Any additional parameters passed into the repo list command
        :type kwargs: dict
        :return: List of docker repositories
        :rtype: list of dict
        """
        all_repos = self._all_repos(query_params, **kwargs)

        docker_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if pulp_constants.REPO_NOTE_TYPE_KEY in notes \
                    and notes[pulp_constants.REPO_NOTE_TYPE_KEY] == constants.REPO_NOTE_DOCKER:
                docker_repos.append(repo)

        return docker_repos

    def get_other_repositories(self, query_params, **kwargs):
        """
         Get a list of all the non docker repositories that match the specified query params

        :param query_params: query parameters for refining the list of repositories
        :type query_params: dict
        :param kwargs: Any additional parameters passed into the repo list command
        :type kwargs: dict
        :return: List of non repositories
        :rtype: list of dict
        """

        all_repos = self._all_repos(query_params, **kwargs)

        non_docker_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if notes.get(pulp_constants.REPO_NOTE_TYPE_KEY, None) != constants.REPO_NOTE_DOCKER:
                non_docker_repos.append(repo)

        return non_docker_repos

    def _all_repos(self, query_params, **kwargs):
        """
        get all the repositories associated with a repo that match a set of query parameters

        :param query_params: query parameters for refining the list of repositories
        :type query_params: dict
        :param kwargs: Any additional parameters passed into the repo list command
        :type kwargs: dict
        :return: list of repositories
        :rtype: list of dict
        """

        # This is safe from any issues with concurrency due to how the CLI works
        if self.all_repos_cache is None:
            self.all_repos_cache = self.context.server.repo.repositories(query_params).response_body

        return self.all_repos_cache
