import logging
import os

from aiohttp import web, web_exceptions
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from gettext import gettext as _
from multidict import MultiDict

from pulpcore.plugin.models import ContentArtifact
from pulp_docker.app.models import DockerDistribution, ManifestTag, ManifestListTag, MEDIA_TYPE


log = logging.getLogger(__name__)


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

    @staticmethod
    async def match_distribution(path):
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
            return DockerDistribution.objects.get(base_path=path)
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

    @staticmethod
    async def tags_list(request):
        """
        Handler for Docker Registry v2 tags/list API.
        """
        path = request.match_info['path']
        distribution = await Registry.match_distribution(path)
        tags = {'name': path, 'tags': set()}
        for c in distribution.publication.repository_version.content:
            c = c.cast()
            if isinstance(c, ManifestTag) or isinstance(c, ManifestListTag):
                tags['tags'].add(c.name)
        tags['tags'] = list(tags['tags'])
        return web.json_response(tags)

    @staticmethod
    async def get_tag(request):
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
        distribution = await Registry.match_distribution(path)
        accepted_media_types = await Registry.get_accepted_media_types(request)
        if MEDIA_TYPE.MANIFEST_LIST in accepted_media_types:
            try:
                tag = ManifestListTag.objects.get(
                    pk__in=distribution.publication.repository_version.content,
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
                    pk__in=distribution.publication.repository_version.content,
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

    @staticmethod
    async def get_by_digest(request):
        """
        Return a response to the "GET" action.
        """
        path = request.match_info['path']
        digest = "sha256:{digest}".format(digest=request.match_info['digest'])
        distribution = await Registry.match_distribution(path)
        log.info(digest)
        try:
            ca = ContentArtifact.objects.get(
                content__in=distribution.publication.repository_version.content,
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
                raise ArtifactNotFound(path)
