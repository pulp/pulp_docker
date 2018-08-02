import logging
from gettext import gettext as _

from pulpcore.plugin.models import RepositoryVersion, Repository
# from pulpcore.plugin.changeset import (
#     BatchIterator,
#     ChangeSet,
#     PendingArtifact,
#     PendingContent,
#     SizedIterable)
from pulpcore.plugin.tasking import WorkingDirectory

from pulp_docker.app.models import DockerRemote


log = logging.getLogger(__name__)


def synchronize(remote_pk, repository_pk):
    """
    Create a new version of the repository that is synchronized with the remote
    as specified by the remote.

    Args:
        remote_pk (str): The remote PK.
        repository_pk (str): The repository PK.

    Raises:
        ValueError: When url is empty.
    """
    remote = DockerRemote.objects.get(pk=remote_pk)
    repository = Repository.objects.get(pk=repository_pk)
    # base_version = RepositoryVersion.latest(repository)

    if not remote.url:
        raise ValueError(_('An remote must have a url specified to synchronize.'))

    with WorkingDirectory():
        # with RepositoryVersion.create(repository) as new_version:
        with RepositoryVersion.create(repository):
            log.info(
                _('Synchronizing: repository=%(r)s remote=%(p)s'),
                {
                    'r': repository.name,
                    'p': remote.name
                })
