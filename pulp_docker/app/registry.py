import logging
import os

from aiohttp import web, web_exceptions
from aiohttp.client_exceptions import ClientResponseError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from gettext import gettext as _
from multidict import MultiDict

from pulpcore.plugin.models import Artifact, ContentArtifact, Remote
from pulp_docker.app.models import DockerDistribution, ManifestTag, ManifestListTag, MEDIA_TYPE


log = logging.getLogger(__name__)


HOP_BY_HOP_HEADERS = [
    'connection',
    'keep-alive',
    'public',
    'proxy-authenticate',
    'transfer-encoding',
    'upgrade',
]


class PathNotResolved(web_exceptions.HTTPNotFound):
    """
    The path could not be resolved to a published file.

    This could be caused by either the distribution, the publication,
    or the published file could not be found.
    """

    def __init__(self, path, *args, **kwargs):
        """Initialize the Exception."""
        self.path = path
        super().__init__(*args, **kwargs)


class ArtifactNotFound(Exception):
    """
    The artifact associated with a published-artifact does not exist.
    """

    pass


class Registry:
    """
    A set of handlers for the Docker v2 API.
    """

    def __init__(self):
        """
        Initializes the Registry class.
        """
        self.distribution_model = DockerDistribution

    @staticmethod
    async def get_accepted_media_types(request):
        """
        Returns a list of media types from the Accept headers.

        Args:
            request(:class:`~aiohttp.web.Request`): The request to extract headers from.

        Returns:
            List of media types supported by the client.

        """
        accepted_media_types = []
        for header, value in request.raw_headers:
            if header == b'Accept':
                accepted_media_types.append(value.decode('UTF-8'))
        return accepted_media_types

    async def match_distribution(self, path):
        """
        Match a distribution using a base path.

        Args:
            path (str): The path component of the URL.

        Returns:
            DockerDistribution: The matched docker distribution.

        Raises:
            PathNotResolved: when not matched.

        """
        try:
            return self.distribution_model.objects.get(base_path=path)
        except ObjectDoesNotExist:
            log.debug(_('DockerDistribution not matched for {path}.').format(path=path))
            raise PathNotResolved(path)

    @staticmethod
    async def _dispatch(path, headers):
        """
        Stream a file back to the client.

        Stream the bits.

        Args:
            path (str): The fully qualified path to the file to be served.
            headers (dict):

        Returns:
            StreamingHttpResponse: Stream the requested content.

        """
        full_headers = MultiDict()

        full_headers['Content-Type'] = headers['Content-Type']
        full_headers['Docker-Distribution-API-Version'] = 'registry/2.0'
        full_headers['Content-Length'] = os.path.getsize(path)
        full_headers['Content-Disposition'] = 'attachment; filename={n}'.format(
            n=os.path.basename(path))
        file_response = web.FileResponse(path, headers=full_headers)
        return file_response

    @staticmethod
    async def serve_v2(request):
        """
        Handler for Docker Registry v2 root.

        The docker client uses this endpoint to discover that the V2 API is available.
        """
        return web.json_response({})

    async def tags_list(self, request):
        """
        Handler for Docker Registry v2 tags/list API.
        """
        path = request.match_info['path']
        distribution = await self.match_distribution(path)
        tags = {'name': path, 'tags': set()}
        repository_version = distribution.get_repository_version()
        for c in repository_version.content:
            c = c.cast()
            if isinstance(c, ManifestTag) or isinstance(c, ManifestListTag):
                tags['tags'].add(c.name)
        tags['tags'] = list(tags['tags'])
        return web.json_response(tags)

    async def get_tag(self, request):
        """
        Match the path and stream either Manifest or ManifestList.

        Args:
            request(:class:`~aiohttp.web.Request`): The request to prepare a response for.

        Raises:
            PathNotResolved: The path could not be matched to a published file.
            PermissionError: When not permitted.

        Returns:
            :class:`aiohttp.web.StreamResponse` or :class:`aiohttp.web.FileResponse`: The response
                streamed back to the client.

        """
        path = request.match_info['path']
        tag_name = request.match_info['tag_name']
        distribution = await self.match_distribution(path)
        repository_version = distribution.get_repository_version()
        accepted_media_types = await Registry.get_accepted_media_types(request)
        if MEDIA_TYPE.MANIFEST_LIST in accepted_media_types:
            try:
                tag = ManifestListTag.objects.get(
                    pk__in=repository_version.content,
                    name=tag_name
                )
            # If there is no manifest list tag, try again with manifest tag.
            except ObjectDoesNotExist:
                pass
            else:
                response_headers = {'Content-Type': MEDIA_TYPE.MANIFEST_LIST}
                return await Registry.dispatch_tag(tag, response_headers)

        if MEDIA_TYPE.MANIFEST_V2 in accepted_media_types:
            try:
                tag = ManifestTag.objects.get(
                    pk__in=repository_version.content,
                    name=tag_name
                )
            except ObjectDoesNotExist:
                raise PathNotResolved(tag_name)
            else:
                response_headers = {'Content-Type': MEDIA_TYPE.MANIFEST_V2}
                return await Registry.dispatch_tag(tag, response_headers)

        else:
            # This is where we could eventually support on-the-fly conversion to schema 1.
            log.warn("Client does not accept Docker V2 Schema 2 and is not currently supported.")
            raise PathNotResolved(path)

    @staticmethod
    async def dispatch_tag(tag, response_headers):
        """
        Finds an artifact associated with a Tag and sends it to the client.

        Args:
            tag: Either a ManifestTag or ManifestListTag
            response_headers (dict): dictionary that contains the 'Content-Type' header to send
                with the response

        Returns:
            :class:`aiohttp.web.StreamResponse` or :class:`aiohttp.web.FileResponse`: The response
                streamed back to the client.

        """
        try:
            artifact = tag._artifacts.get()
        except ObjectDoesNotExist:
            raise ArtifactNotFound(tag.name)
        else:
            return await Registry._dispatch(os.path.join(settings.MEDIA_ROOT, artifact.file.name),
                                            response_headers)

    async def get_by_digest(self, request):
        """
        Return a response to the "GET" action.
        """
        path = request.match_info['path']
        digest = "sha256:{digest}".format(digest=request.match_info['digest'])
        distribution = await self.match_distribution(path)
        repository_version = distribution.get_repository_version()
        log.info(digest)
        try:
            ca = ContentArtifact.objects.get(content__in=repository_version.content,
                                             relative_path=digest)
            headers = {'Content-Type': ca.content.cast().media_type}
        except ObjectDoesNotExist:
            raise PathNotResolved(path)
        else:
            artifact = ca.artifact
            if artifact:
                return await Registry._dispatch(os.path.join(settings.MEDIA_ROOT,
                                                             artifact.file.name),
                                                headers)
            else:
                return await self._stream_content_artifact(request, web.StreamResponse(), ca)

    async def _stream_content_artifact(self, request, response, content_artifact):
        """
        Stream and optionally save a ContentArtifact by requesting it using the associated remote.

        If a fatal download failure occurs while downloading and there are additional
        :class:`~pulpcore.plugin.models.RemoteArtifact` objects associated with the
        :class:`~pulpcore.plugin.models.ContentArtifact` they will also be tried. If all
        :class:`~pulpcore.plugin.models.RemoteArtifact` downloads raise exceptions, an HTTP 502
        error is returned to the client.

        Args:
            request(:class:`~aiohttp.web.Request`): The request to prepare a response for.
            response (:class:`~aiohttp.web.StreamResponse`): The response to stream data to.
            content_artifact (:class:`~pulpcore.plugin.models.ContentArtifact`): The ContentArtifact
                to fetch and then stream back to the client

        Raises:
            :class:`~aiohttp.web.HTTPNotFound` when no
                :class:`~pulpcore.plugin.models.RemoteArtifact` objects associated with the
                :class:`~pulpcore.plugin.models.ContentArtifact` returned the binary data needed for
                the client.

        """
        for remote_artifact in content_artifact.remoteartifact_set.all():
            try:
                response = await self._stream_remote_artifact(request, response, remote_artifact)

            except ClientResponseError:
                continue

        raise web_exceptions.HTTPNotFound()

    async def _stream_remote_artifact(self, request, response, remote_artifact):
        """
        Stream and save a RemoteArtifact.

        Args:
            request(:class:`~aiohttp.web.Request`): The request to prepare a response for.
            response (:class:`~aiohttp.web.StreamResponse`): The response to stream data to.
            content_artifact (:class:`~pulpcore.plugin.models.ContentArtifact`): The ContentArtifact
                to fetch and then stream back to the client

        Raises:
            :class:`~aiohttp.web.HTTPNotFound` when no
                :class:`~pulpcore.plugin.models.RemoteArtifact` objects associated with the
                :class:`~pulpcore.plugin.models.ContentArtifact` returned the binary data needed for
                the client.

        """
        remote = remote_artifact.remote.cast()

        async def handle_headers(headers):
            for name, value in headers.items():
                if name.lower() in HOP_BY_HOP_HEADERS:
                    continue
                response.headers[name] = value
            await response.prepare(request)

        async def handle_data(data):
            await response.write(data)
            if remote.policy != Remote.STREAMED:
                await original_handle_data(data)

        async def finalize():
            if remote.policy != Remote.STREAMED:
                await original_finalize()

        repo_name = remote.namespaced_upstream_name
        downloader = remote.get_downloader(remote_artifact=remote_artifact,
                                           headers_ready_callback=handle_headers)
        original_handle_data = downloader.handle_data
        downloader.handle_data = handle_data
        original_finalize = downloader.finalize
        downloader.finalize = finalize
        download_result = await downloader.run(extra_data={'repo_name': repo_name})

        if remote.policy != Remote.STREAMED:
            self._save_artifact(download_result, remote_artifact)
        await response.write_eof()
        return response

    def _save_artifact(self, download_result, remote_artifact):
        """
        Create/Get an Artifact and associate it to a RemoteArtifact and/or ContentArtifact.

        Create (or get if already existing) an :class:`~pulpcore.plugin.models.Artifact`
        based on the `download_result` and associate it to the `content_artifact` of the given
        `remote_artifact`. Both the created artifact and the updated content_artifact are saved to
        the DB.  The `remote_artifact` is also saved for the pull-through caching use case.

        Plugin-writers may overide this method if their content module requires
        additional/different steps for saving.

        Args:
            download_result (:class:`~pulpcore.plugin.download.DownloadResult`: The
                DownloadResult for the downloaded artifact.

            remote_artifact (:class:`~pulpcore.plugin.models.RemoteArtifact`): The
                RemoteArtifact to associate the Artifact with.

        Returns:
            The associated :class:`~pulpcore.plugin.models.Artifact`.

        """
        content_artifact = remote_artifact.content_artifact
        remote = remote_artifact.remote
        artifact = Artifact(
            **download_result.artifact_attributes,
            file=download_result.path
        )
        with transaction.atomic():
            try:
                with transaction.atomic():
                    artifact.save()
            except IntegrityError:
                artifact = Artifact.objects.get(artifact.q())
            update_content_artifact = True
            if content_artifact._state.adding:
                # This is the first time pull-through content was requested.
                rel_path = content_artifact.relative_path
                c_type = remote.get_remote_artifact_content_type(rel_path)
                content = c_type.init_from_artifact_and_relative_path(artifact, rel_path)
                try:
                    with transaction.atomic():
                        content.save()
                        content_artifact.content = content
                        content_artifact.save()
                except IntegrityError:
                    # There is already content for this Artifact
                    content = c_type.objects.get(content.q())
                    artifacts = content._artifacts
                    if artifact.sha256 != artifacts[0].sha256:
                        raise RuntimeError("The Artifact downloaded during pull-through does not "
                                           "match the Artifact already stored for the same "
                                           "content.")
                    content_artifact = ContentArtifact.objects.get(content=content)
                    update_content_artifact = False
                try:
                    with transaction.atomic():
                        remote_artifact.content_artifact = content_artifact
                        remote_artifact.save()
                except IntegrityError:
                    # Remote artifact must have already gotten saved during a parallel request
                    log.info("RemoteArtifact already exists.")
            if update_content_artifact:
                content_artifact.artifact = artifact
                content_artifact.save()
        return artifact
