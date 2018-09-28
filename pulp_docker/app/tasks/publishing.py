import logging
from gettext import gettext as _

from pulpcore.plugin.models import (  # noqa
    RepositoryVersion,
    Publication
)

from pulp_docker.app.models import DockerPublisher


log = logging.getLogger(__name__)


def publish(publisher_pk, repository_version_pk):
    """
    Use provided publisher to create a Publication based on a RepositoryVersion.

    Args:
        publisher_pk (str): Use the publish settings provided by this publisher.
        repository_version_pk (str): Create a publication from this repository version.
    """
    publisher = DockerPublisher.objects.get(pk=publisher_pk)
    repository_version = RepositoryVersion.objects.get(pk=repository_version_pk)

    log.info(_('Publishing: repository={repo}, version={ver}, publisher={pub}').format(
        repo=repository_version.repository.name,
        ver=repository_version.number,
        pub=publisher.name
    ))

    with Publication.create(repository_version, publisher, pass_through=True) as publication:
        pass

    log.info(_('Publication: {publication} created').format(publication.pk))
