from gettext import gettext as _

from django.conf import settings
from django.core import validators

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from pulpcore.plugin.serializers import (
    BaseDistributionSerializer,
    DetailRelatedField,
    IdentityField,
    NestedRelatedField,
    RemoteSerializer,
    SingleArtifactContentSerializer,
)

from . import models


class ManifestListTagSerializer(SingleArtifactContentSerializer):
    """
    Serializer for ManifestListTags.
    """

    name = serializers.CharField(help_text="Tag name")
    manifest_list = DetailRelatedField(
        many=False,
        help_text="Manifest List that is tagged",
        view_name='docker-manifest-lists-detail',
        queryset=models.ManifestList.objects.all()
    )

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            'name',
            'manifest_list',
        )
        model = models.ManifestListTag


class ManifestTagSerializer(SingleArtifactContentSerializer):
    """
    Serializer for ManifestTags.
    """

    name = serializers.CharField(help_text="Tag name")
    manifest = DetailRelatedField(
        many=False,
        help_text="Manifest that is tagged",
        view_name='docker-manifests-detail',
        queryset=models.ImageManifest.objects.all()
    )

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            'name',
            'manifest',
        )
        model = models.ManifestTag


class ManifestListSerializer(SingleArtifactContentSerializer):
    """
    Serializer for ManifestLists.
    """

    digest = serializers.CharField(help_text="sha256 of the ManifestList file")
    schema_version = serializers.IntegerField(help_text="Docker schema version")
    media_type = serializers.CharField(help_text="Docker media type of the file")
    manifests = DetailRelatedField(
        many=True,
        help_text="Manifests that are referenced by this Manifest List",
        view_name='docker-manifests-detail',
        queryset=models.ImageManifest.objects.all()
    )

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            'digest',
            'schema_version',
            'media_type',
            'manifests',
        )
        model = models.ManifestList


class ManifestSerializer(SingleArtifactContentSerializer):
    """
    Serializer for Manifests.
    """

    digest = serializers.CharField(help_text="sha256 of the Manifest file")
    schema_version = serializers.IntegerField(help_text="Docker schema version")
    media_type = serializers.CharField(help_text="Docker media type of the file")
    blobs = DetailRelatedField(
        many=True,
        help_text="Blobs that are referenced by this Manifest",
        view_name='docker-blobs-detail',
        queryset=models.ManifestBlob.objects.all()
    )
    config_blob = DetailRelatedField(
        many=False,
        help_text="Blob that contains configuration for this Manifest",
        view_name='docker-blobs-detail',
        queryset=models.ManifestBlob.objects.all()
    )

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            'digest',
            'schema_version',
            'media_type',
            'blobs',
            'config_blob',
        )
        model = models.ImageManifest


class BlobSerializer(SingleArtifactContentSerializer):
    """
    Serializer for Blobs.
    """

    digest = serializers.CharField(help_text="sha256 of the Blob file")
    media_type = serializers.CharField(help_text="Docker media type of the file")

    class Meta:
        fields = SingleArtifactContentSerializer.Meta.fields + (
            'digest',
            'media_type',
        )
        model = models.ManifestBlob


class RegistryPathField(serializers.CharField):
    """
    Serializer Field for the registry_path field of the DockerDistribution.
    """

    def to_representation(self, value):
        """
        Converts a base_path into a registry path.
        """
        if settings.CONTENT_HOST:
            host = settings.CONTENT_HOST
        else:
            host = self.context['request'].get_host()
        return ''.join([host, '/', value])


class DockerRemoteSerializer(RemoteSerializer):
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
    whitelist_tags = serializers.CharField(
        required=False,
        help_text=_("Whitelist tags to sync")
    )

    class Meta:
        fields = RemoteSerializer.Meta.fields + ('upstream_name', 'whitelist_tags',)
        model = models.DockerRemote


class DockerDistributionSerializer(BaseDistributionSerializer):
    """
    A serializer for DockerDistribution.
    """

    _href = IdentityField(
        view_name='docker-distributions-detail'
    )
    name = serializers.CharField(
        help_text=_('A unique distribution name. Ex, `rawhide` and `stable`.'),
        validators=[validators.MaxLengthValidator(
            models.DockerDistribution._meta.get_field('name').max_length,
            message=_('DockerDistribution name length must be less than {} characters').format(
                models.DockerDistribution._meta.get_field('name').max_length
            )),
            UniqueValidator(queryset=models.DockerDistribution.objects.all())]
    )
    base_path = serializers.CharField(
        help_text=_('The base (relative) path that identifies the registry path.'),
        validators=[validators.MaxLengthValidator(
            models.DockerDistribution._meta.get_field('base_path').max_length,
            message=_('Distribution base_path length must be less than {} characters').format(
                models.DockerDistribution._meta.get_field('base_path').max_length
            )),
            UniqueValidator(queryset=models.DockerDistribution.objects.all()),
        ]
    )
    registry_path = RegistryPathField(
        source='base_path', read_only=True,
        help_text=_('The Registry hostame:port/name/ to use with docker pull command defined by '
                    'this distribution.')
    )
    repository_version = NestedRelatedField(
        help_text=_('A URI of the repository version to be served by the Docker Distribution.'),
        required=False,
        label=_('Repository Version'),
        queryset=models.RepositoryVersion.objects.all(),
        view_name='versions-detail',
        lookup_field='number',
        parent_lookup_kwargs={'repository_pk': 'repository__pk'},
    )

    def validate(self, data):
        """
        Validate the parameters for creating or updating Docker Distribution.

        This method makes sure that only repository or a repository version is associated with a
        Docker Distribution. It also validates that the base_path is a relative path.

        Args:
            data (dict): Dictionary of parameter value to validate

        Returns:
            Dict of validated data

        Raises:
            ValidationError if any of the validations fail.

        """
        super().validate(data)
        if 'repository' in data:
            repository = data['repository']
        elif self.instance:
            repository = self.instance.repository
        else:
            repository = None

        if 'repository_version' in data:
            repository_version = data['repository_version']
        elif self.instance:
            repository_version = self.instance.repository_version
        else:
            repository_version = None

        if repository and repository_version:
            raise serializers.ValidationError({'repository': _("Repository can't be set if "
                                                               "repository_version is set also.")})
        if 'publication' in data and data['publication']:
            raise serializers.ValidationError({'publication': _("DockerDistributions don't serve "
                                                                "publications. A repository or "
                                                                "repository version should be "
                                                                "specified.")})
        if 'publisher' in data and data['publisher']:
            raise serializers.ValidationError({'publication': _("DockerDistributions don't work "
                                                                "with publishers. A repository or "
                                                                "a repository version should be "
                                                                "specified.")})
        if 'base_path' in data and data['base_path']:
            self._validate_relative_path(data['base_path'])

        return data

    class Meta:
        model = models.DockerDistribution
        fields = BaseDistributionSerializer.Meta.fields + ('base_path',
                                                           'registry_path',
                                                           'repository_version')
