"""
Check `Plugin Writer's Guide`_ and `pulp_example`_ plugin
implementation for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html

.. _pulp_example:
    https://github.com/pulp/pulp_example/
"""

from gettext import gettext as _
from logging import getLogger

from django.db import models

from pulpcore.plugin.models import (Artifact, Content, ContentArtifact, RemoteArtifact, Remote,
                                    ProgressBar, Publisher, RepositoryVersion, PublishedArtifact,
                                    PublishedMetadata)
from pulpcore.plugin.tasking import Task


log = getLogger(__name__)


class DockerContent(Content):
    """
    The "docker" content type.

    Define fields you need for your new content type and
    specify uniqueness constraint to identify unit of this type.

    For example::

        field1 = models.TextField()
        field2 = models.IntegerField()
        field3 = models.CharField()

        class Meta:
            unique_together = (field1, field2)
    """

    TYPE = 'docker'


class DockerPublisher(Publisher):
    """
    A Publisher for DockerContent.

    Define any additional fields for your new publisher if needed.
    A ``publish`` method should be defined.
    It is responsible for publishing metadata and artifacts
    which belongs to a specific repository.
    """

    TYPE = 'docker'

    def publish(self):
        """
        Publish the repository.
        """
        raise NotImplementedError


class DockerRemote(Remote):
    """
    A Remote for DockerContent.

    Define any additional fields for your new importer if needed.
    A ``sync`` method should be defined.
    It is responsible for parsing metadata of the content,
    downloading of the content and saving it to Pulp.
    """

    TYPE = 'docker'

    def sync(self, new_version, base_version):
        """
        Synchronize the repository with the remote repository. Generates a new RepositoryVersion

        Args:
            new_version (pulpcore.plugin.models.RepositoryVersion): the new version to which
                content should be added and removed.
            base_version (pulpcore.plugin.models.RepositoryVersion): the targeted pre-existing
                version or None if one does not exist.

        """
        raise NotImplementedError
