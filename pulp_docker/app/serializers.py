"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""
from gettext import gettext as _
from rest_framework import serializers  # noqa

from pulpcore.plugin import serializers as platform

from . import models


class DockerRemoteSerializer(platform.RemoteSerializer):
    """
    A Serializer for DockerRemote.

    Add any new fields if defined on DockerRemote.
    Similar to the example above, in DockerContentSerializer.
    Additional validators can be added to the parent validators list

    For example::

    class Meta:
        validators = platform.RemoteSerializer.Meta.validators + [myValidator1, myValidator2]
    """
    upstream_name = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text=_("Name of the upstream repository")
    )

    class Meta:
        fields = platform.RemoteSerializer.Meta.fields + ('upstream_name',)
        model = models.DockerRemote


class DockerPublisherSerializer(platform.PublisherSerializer):
    """
    A Serializer for DockerPublisher.

    Add any new fields if defined on DockerPublisher.
    Similar to the example above, in DockerContentSerializer.
    Additional validators can be added to the parent validators list

    For example::

    class Meta:
        validators = platform.PublisherSerializer.Meta.validators + [myValidator1, myValidator2]
    """
    class Meta:
        fields = platform.PublisherSerializer.Meta.fields
        model = models.DockerPublisher
