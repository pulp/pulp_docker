"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""
import logging
from tempfile import NamedTemporaryFile

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.http.response import StreamingHttpResponse
from django.http import Http404
from drf_yasg.utils import swagger_auto_schema
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)

from pulpcore.plugin.models import Artifact, ContentArtifact, Repository, RepositoryVersion
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.viewsets import (
    BaseDistributionViewSet,
    ContentFilter,
    ContentViewSet,
    RemoteViewSet,
    OperationPostponedResponse,)
from rest_framework.decorators import detail_route
from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView

from . import models, serializers, tasks


log = logging.getLogger(__name__)


class ManifestTagFilter(ContentFilter):
    """
    FilterSet for Tags.
    """

    class Meta:
        model = models.ManifestTag
        fields = [
            'name',
        ]


class ManifestTagViewSet(ContentViewSet):
    """
    ViewSet for ManifestTag.
    """

    endpoint_name = 'manifest-tags'
    queryset = models.ManifestTag.objects.all()
    serializer_class = serializers.ManifestTagSerializer
    filterset_class = ManifestTagFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a new ManifestTag from a request.
        """
        raise NotImplementedError()


class ManifestViewSet(ContentViewSet):
    """
    ViewSet for Manifest.
    """

    endpoint_name = 'manifests'
    queryset = models.Manifest.objects.all()
    serializer_class = serializers.ManifestSerializer

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

    class Meta:
        model = models.ManifestBlob
        fields = [
            'digest',
        ]


class BlobViewSet(ContentViewSet):
    """
    ViewSet for ManifestBlobs.
    """

    endpoint_name = 'blobs'
    queryset = models.ManifestBlob.objects.all()
    serializer_class = serializers.BlobSerializer
    filterset_class = BlobFilter

    @transaction.atomic
    def create(self, request):
        """
        Create a new ManifestBlob from a request.
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
    @detail_route(methods=('post',), serializer_class=RepositorySyncURLSerializer)
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


from rest_framework.response import Response
import hashlib
import re
from django.core.files.base import ContentFile

class UploadResponse(Response):
    """
    An HTTP response class for returning 202 and a spawned task.

    This response object should be used by views that dispatch asynchronous tasks. The most common
    use case is for sync and publish operations. When JSON is requested, the response will look
    like the following::

        {
            "_href": "https://example.com/pulp/api/v3/tasks/adlfk-bala-23k5l7-lslser",
            "task_id": "adlfk-bala-23k5l7-lslser"
        }
    """

    def __init__(self, upload, path, content_length, request):
        """
        Args:
            task_result (pulpcore.app.models.Task): A :class:`rq.job.Job` object used to generate
                the response.
            request (rest_framework.request.Request): Request used to generate the _href urls
        """
        headers = {'Docker-Distribution-Api-Version': 'registry/2.0',
                   'Docker-Upload-UUID': upload.pk,
                   'Location': '/v2/{path}/blobs/uploads/{pk}'.format(path=path, pk=upload.pk),
                   'Range': '0-{offset}'.format(offset=upload.file.size),
                   'Content-Length': 0
                   }
        super().__init__(headers=headers, status=202)


class ManifestResponse(Response):
    """
    An HTTP response class for returning 202 and a spawned task.

    This response object should be used by views that dispatch asynchronous tasks. The most common
    use case is for sync and publish operations. When JSON is requested, the response will look
    like the following::

        {
            "_href": "https://example.com/pulp/api/v3/tasks/adlfk-bala-23k5l7-lslser",
            "task_id": "adlfk-bala-23k5l7-lslser"
        }
    """

    def __init__(self, manifest, path, request, status=200, send_body=False):
        """
        Args:
            task_result (pulpcore.app.models.Task): A :class:`rq.job.Job` object used to generate
                the response.
            request (rest_framework.request.Request): Request used to generate the _href urls
        """
        artifact = manifest._artifacts.get()
        if send_body:
            size = artifact.size
        else:
            size = 0
        headers = {'Docker-Distribution-Api-Version': 'registry/2.0',
                   'Docker-Content-Digest': manifest.digest,
                   'Location': '/v2/{path}/manifests/{digest}'.format(path=path, digest=manifest.digest),
                   'Content-Length': size
                   }
        if send_body:
            super().__init__(data=artifact.file, headers=headers, status=status)
        else:
            super().__init__(headers=headers, status=status)


class BlobResponse(Response):
    """
    An HTTP response class for returning 202 and a spawned task.

    This response object should be used by views that dispatch asynchronous tasks. The most common
    use case is for sync and publish operations. When JSON is requested, the response will look
    like the following::

        {
            "_href": "https://example.com/pulp/api/v3/tasks/adlfk-bala-23k5l7-lslser",
            "task_id": "adlfk-bala-23k5l7-lslser"
        }
    """

    def __init__(self, blob, path, status, request, send_body=False):
        """
        Args:
            blob (pulpcore.app.models.Task): A :class:`rq.job.Job` object used to generate
                the response.
            request (rest_framework.request.Request): Request used to generate the _href urls
        """
        artifact = blob._artifacts.get()
        size = artifact.size

        log.info('digest: {digest}'.format(digest=blob.digest))
        headers = {'Docker-Distribution-Api-Version': 'registry/2.0',
                   'Docker-Content-Digest': blob.digest,
                   'Location': '/v2/{path}/blobs/{digest}'.format(path=path, digest=blob.digest),
                   'Etag': blob.digest,
                   'Range': '0-{offset}'.format(offset=int(size)),
                   'Content-Length': size,
                   'Content-Type': 'application/octet-stream',
                   'Connection': 'close'
                   }
        if send_body:
            super().__init__(data=artifact.file, headers=headers, status=status)
        else:
            super().__init__(headers=headers, status=status)

class VersionView(APIView):
    """
    Handles requests to the /v2/ endpoint.
    """
    # allow anyone to access
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        headers = {'Docker-Distribution-Api-Version': 'registry/2.0',
                   }
        return Response(data={}, headers=headers)

class BlobUploads(ViewSet):
    """
    The ViewSet for handling uploading of blobs.
    """
    model = models.Upload
    queryset = models.Upload.objects.all()

    # allow anyone to access
    authentication_classes = []
    permission_classes = []

    content_range_pattern = re.compile(r'^(?P<start>\d+)-(?P<end>\d+)$')

    def create(self, request, path):
        """
        This methods handles the creation of an upload.
        """
        repository = get_object_or_404(Repository, name=path)
        upload = models.Upload(repository=repository)
        upload.file.save(name='', content=ContentFile(''), save=False)
        upload.save()
        response = UploadResponse(upload=upload, path=path, content_length=0, request=request)

        return response

    def partial_update(self, request, path, pk=None):
        """
        This methods handles uploading of a chunk to an existing upload.
        """
        repository = get_object_or_404(Repository, name=path)
        chunk = request.META['wsgi.input']
        try:
            digest = request.query_params['digest']
            try:
                content_range = request.headers['Content-Range']
                whole = False
            except KeyError:
                whole = True
        except KeyError:
            whole = False

        if whole:
            start = 0
            end = chunk.size - 1
        else:
            content_range = request.META.get('HTTP_CONTENT_RANGE', '')
            match = self.content_range_pattern.match(content_range)
            if not match:
                start = 0
                end = 0
                chunk_size = 0
            else:
                start = int(match.group('start'))
                end = int(match.group('end'))
                chunk_size = end - start + 1

        upload = get_object_or_404(models.Upload, repository=repository, pk=pk)

        if upload.offset != start:
            raise Exception
        upload.append_chunk(chunk, chunk_size=chunk_size)
        upload.save()
        return UploadResponse(upload=upload, path=path, content_length=upload.file.size, request=request)

    def put(self, request, path, pk=None):
        repository = get_object_or_404(Repository, name=path)
        try:
            digest = request.query_params['digest']
            try:
                content_range = request.headers['Content-Range']
                whole = False
            except KeyError:
                whole = True
        except KeyError:
            whole = False
        upload = models.Upload.objects.get(pk=pk, repository=repository)


        if upload.sha256 == digest[len("sha256:"):]:
            try:
                artifact = Artifact(file=upload.file.name, md5=upload.md5, sha1=upload.sha1, sha256=upload.sha256, sha384=upload.sha384, sha512=upload.sha512, size=upload.file.size)
                artifact.save()
            except IntegrityError:
                artifact = Artifact.objects.get(sha256=artifact.sha256)
            try:
                blob = models.ManifestBlob(digest=digest, media_type=models.MEDIA_TYPE.REGULAR_BLOB)
                blob.save()
            except IntegrityError:
                blob = models.ManifestBlob.objects.get(digest=digest)
            try:
                blob_artifact = ContentArtifact(artifact=artifact, content=blob, relative_path=digest)
                blob_artifact.save()
            except IntegrityError:
                pass

            with RepositoryVersion.create(repository, in_task=False) as new_version:
                new_version.add_content(models.ManifestBlob.objects.filter(pk=blob.pk))

            upload.delete()

            return BlobResponse(blob, path, 201, request)
        else:
            raise Exception("The digest did not match")

class Blobs(ViewSet):
    """
    ViewSet for intereacting with Blobs
    """
    # allow anyone to access
    authentication_classes = []
    permission_classes = []

    def head(self, request, path, pk=None):
        """
        Responds to HEAD requests about blobs
        :param request:
        :param path:
        :param digest:
        :return:
        """
        repository = get_object_or_404(Repository, name=path)
        repository_version = RepositoryVersion.latest(repository)
        if not repository_version:
            raise Http404("Blob does not exist: {digest}".format(digest=pk))
        blob = get_object_or_404(models.ManifestBlob, digest=pk, pk__in=repository_version.content)
        return BlobResponse(blob, path, 200, request)

    def get(self, request, path, pk=None):
        repository = get_object_or_404(Repository, name=path)
        repository_version = RepositoryVersion.latest(repository)
        blob = get_object_or_404(models.ManifestBlob, digest=pk, pk__in=repository_version.content)
        return BlobResponse(blob, path, 200, request, True)

class Manifests(ViewSet):
    """
    ViewSet for intereacting with Manifests
    """
    # allow anyone to access
    authentication_classes = []
    permission_classes = []

    def head(self, request, path, pk=None):
        """
        Responds to HEAD requests about blobs
        :param request:
        :param path:
        :param digest:
        :return:
        """
        try:
            manifest = models.Manifest.objects.get(digest=pk)
        except models.Manifest.DoesNotExist:
            manifest = get_object_or_404(models.ManifestList, digest=pk)

        return ManifestResponse(manifest, path, request)

    def get(self, request, path, pk=None):
        """
        Responds to HEAD requests about blobs
        :param request:
        :param path:
        :param digest:
        :return:
        """
        digest = None
        tag = None
        if pk[:7] == 'sha256:':
            digest = pk
        else:
            tag = pk
        if tag:
            tag = get_object_or_404(models.ManifestListTag, name=tag)
            manifest = tag.manifest_list
        else:
            try:
                manifest = models.Manifest.objects.get(digest=pk)
            except models.Manifest.DoesNotExist:
                manifest = get_object_or_404(models.Manifest, digest=pk)

        return ManifestResponse(manifest, path, request, send_body=True)

    def put(self, request, path, pk=None):
        """
        Responds with the actual blob
        :param request:
        :param path:
        :param pk:
        :return:
        """
        repository = get_object_or_404(Repository, name=path)

        # iterate over all the layers and create
        chunk = request.META['wsgi.input']
        artifact = self.receive_artifact(chunk)

        manifest = models.Manifest(digest="sha256:{id}".format(id=artifact.sha256), schema_version=2)
        try:
            manifest.save()
        except IntegrityError:
            manifest = models.Manifest.objects.get(digest=manifest.digest)
        ca = ContentArtifact(artifact=artifact, content=manifest, relative_path=manifest.digest)
        try:
            ca.save()
        except IntegrityError:
            pass
        tag = models.ManifestTag(name=pk, tagged_manifest=manifest)
        try:
            tag.save()
        except IntegrityError:
            pass
        with RepositoryVersion.create(repository, in_task=False) as new_version:
            new_version.add_content(models.Manifest.objects.filter(digest=manifest.digest))
            new_version.remove_content(models.ManifestTag.objects.filter(name=tag.name))
            new_version.add_content(models.ManifestTag.objects.filter(name=tag.name, tagged_manifest=manifest))
        return ManifestResponse(manifest, path, request, status=201)

    def receive_artifact(self, chunk):
        temp_file = NamedTemporaryFile('ab')
        size = 0
        hashers = {}
        for algorithm in Artifact.DIGEST_FIELDS:
            hashers[algorithm] = getattr(hashlib, algorithm)()
        while True:
            subchunk = chunk.read(2000000)
            if not subchunk:
                break
            temp_file.write(subchunk)
            size += len(subchunk)
            for algorithm in Artifact.DIGEST_FIELDS:
                hashers[algorithm].update(subchunk)

        digests = {}
        for algorithm in Artifact.DIGEST_FIELDS:
            digests[algorithm] = hashers[algorithm].hexdigest()
        artifact = Artifact(file=temp_file.name, size=size, **digests)
        try:
            artifact.save()
        except IntegrityError:
            artifact = Artifact.objects.get(sha256=artifact.sha256)
        return artifact
