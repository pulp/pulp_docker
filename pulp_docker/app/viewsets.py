"""
Check `Plugin Writer's Guide`_ for more details.

. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""

from django_filters import MultipleChoiceFilter
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.models import Content
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.viewsets import (
    BaseDistributionViewSet,
    CharInFilter,
    ContentFilter,
    ContentViewSet,
    NamedModelViewSet,
    RemoteViewSet,
    OperationPostponedResponse,
)
from rest_framework import viewsets as drf_viewsets
from rest_framework.decorators import action

from . import models, serializers, tasks


class TagFilter(ContentFilter):
    """
    FilterSet for Tags.
    """

    media_type = MultipleChoiceFilter(
        choices=models.Manifest.MANIFEST_CHOICES,
        field_name='tagged_manifest__media_type',
        lookup_expr='contains',
    )
    digest = CharInFilter(field_name='tagged_manifest__digest', lookup_expr='in')

    class Meta:
        model = models.Tag
        fields = {
            'name': ['exact', 'in'],
        }


class ManifestFilter(ContentFilter):
    """
    FilterSet for Manifests.
    """

    media_type = MultipleChoiceFilter(choices=models.Manifest.MANIFEST_CHOICES)

    class Meta:
        model = models.Manifest
        fields = {
            'digest': ['exact', 'in'],
        }


class TagViewSet(ContentViewSet):
    """
    ViewSet for Tag.
    """

    endpoint_name = 'tags'
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer
    filterset_class = TagFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a new Tag from a request.
        """
        raise NotImplementedError()


class ManifestViewSet(ContentViewSet):
    """
    ViewSet for Manifest.
    """

    endpoint_name = 'manifests'
    queryset = models.Manifest.objects.all()
    serializer_class = serializers.ManifestSerializer
    filterset_class = ManifestFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a new Manifest from a request.
        """
        raise NotImplementedError()


class BlobFilter(ContentFilter):
    """
    FilterSet for Blobs.
    """

    media_type = MultipleChoiceFilter(choices=models.Blob.BLOB_CHOICES)

    class Meta:
        model = models.Blob
        fields = {
            'digest': ['exact', 'in'],
        }


class BlobViewSet(ContentViewSet):
    """
    ViewSet for Blobs.
    """

    endpoint_name = 'blobs'
    queryset = models.Blob.objects.all()
    serializer_class = serializers.BlobSerializer
    filterset_class = BlobFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a new Blob from a request.
        """
        raise NotImplementedError()


class DockerRemoteViewSet(RemoteViewSet):
    """
    A ViewSet for DockerRemote.
    """

    endpoint_name = 'docker'
    queryset = models.DockerRemote.objects.all()
    serializer_class = serializers.DockerRemoteSerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to sync content",
        responses={202: AsyncOperationResponseSerializer}
    )
    @action(detail=True, methods=['post'], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Synchronizes a repository. The ``repository`` field has to be provided.
        """
        remote = self.get_object()
        serializer = RepositorySyncURLSerializer(data=request.data, context={'request': request})

        # Validate synchronously to return 400 errors.
        serializer.is_valid(raise_exception=True)
        repository = serializer.validated_data.get('repository')
        result = enqueue_with_reservation(
            tasks.synchronize,
            [repository, remote],
            kwargs={
                'remote_pk': remote.pk,
                'repository_pk': repository.pk
            }
        )
        return OperationPostponedResponse(result, request)


class DockerDistributionViewSet(BaseDistributionViewSet):
    """
    ViewSet for DockerDistribution model.
    """

    endpoint_name = 'docker'
    queryset = models.DockerDistribution.objects.all()
    serializer_class = serializers.DockerDistributionSerializer


class TagImageViewSet(drf_viewsets.ViewSet):
    """
    ViewSet used for tagging manifests. This endpoint supports only HTTP POST requests.
    """

    endpoint_name = 'tag'

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to create a new repository",
        responses={202: AsyncOperationResponseSerializer},
        request_body=serializers.TagImageSerializer,
    )
    def create(self, request):
        """
        Create a task which is responsible for initializing a new repository version.
        """
        serializer = serializers.TagImageSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        manifest = serializer.validated_data['manifest']
        tag = serializer.validated_data['tag']
        repository = serializer.validated_data['repository']

        result = enqueue_with_reservation(
            tasks.tag_image,
            [repository, manifest],
            kwargs={
                'manifest_pk': manifest.pk,
                'tag': tag,
                'repository_pk': repository.pk
            }
        )
        return OperationPostponedResponse(result, request)


class UnTagImageViewSet(drf_viewsets.ViewSet):
    """
    ViewSet used for untagging manifests. This endpoint supports only HTTP POST requests.
    """

    endpoint_name = 'untag'

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to create a new repository",
        responses={202: AsyncOperationResponseSerializer},
        request_body=serializers.UnTagImageSerializer,
    )
    def create(self, request):
        """
        Create a task which is responsible for creating a new tag.
        """
        serializer = serializers.UnTagImageSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        tag = serializer.validated_data['tag']
        repository = serializer.validated_data['repository']

        result = enqueue_with_reservation(
            tasks.untag_image,
            [repository],
            kwargs={
                'tag': tag,
                'repository_pk': repository.pk
            }
        )
        return OperationPostponedResponse(result, request)


class RecursiveAdd(drf_viewsets.ViewSet):
    """
    ViewSet for recursively adding and removing Docker content.
    """

    serializer_class = serializers.DockerRecursiveAddSerializer

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to recursively add docker content.",
        responses={202: AsyncOperationResponseSerializer},
        request_body=serializers.DockerRecursiveAddSerializer,
    )
    def create(self, request):
        """
        Queues a task that creates a new RepositoryVersion by adding content units.
        """
        add_content_units = []
        serializer = serializers.DockerRecursiveAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository = serializer.validated_data['repository']

        if 'content_units' in request.data:
            for url in request.data['content_units']:
                content = NamedModelViewSet.get_resource(url, Content)
                add_content_units.append(content.pk)

        result = enqueue_with_reservation(
            tasks.recursive_add_content, [repository],
            kwargs={
                'repository_pk': repository.pk,
                'content_units': add_content_units,
            }
        )
        return OperationPostponedResponse(result, request)


class TagCopyViewSet(drf_viewsets.ViewSet):
    """
    ViewSet for copying tags recursively.
    """

    serializer_class = serializers.TagCopySerializer

    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to copy tags",
        responses={202: AsyncOperationResponseSerializer},
        request_body=serializers.TagCopySerializer,
    )
    def create(self, request):
        """
        Queues a task that creates a new RepositoryVersion by adding content units.
        """
        names = request.data.get("names")
        serializer = serializers.TagCopySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source_latest = serializer.validated_data['source_repository_version']
        destination = serializer.validated_data['destination_repository']
        content_tags_in_repo = source_latest.content.filter(
            _type="docker.tag"
        )
        tags_in_repo = models.Tag.objects.filter(
            pk__in=content_tags_in_repo,
        )
        if names is None:
            tags_to_add = tags_in_repo
        else:
            tags_to_add = tags_in_repo.filter(name__in=names)

        result = enqueue_with_reservation(
            tasks.recursive_add_content, [destination],
            kwargs={
                'repository_pk': destination.pk,
                'content_units': tags_to_add.values_list('pk', flat=True),
            }
        )
        return OperationPostponedResponse(result, request)
