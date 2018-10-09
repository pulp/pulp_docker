import os

from gettext import gettext as _

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    HttpResponseForbidden,
    HttpResponseNotFound,
    StreamingHttpResponse)

from wsgiref.util import FileWrapper

from pulpcore.plugin.models import ContentArtifact
from pulpcore.app.views.content import ArtifactNotFound, PathNotResolved

from pulp_docker.app.models import DockerDistribution, Tag

from rest_framework.negotiation import BaseContentNegotiation
from rest_framework import response, views


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """
    Content negotiation class that ignores the accept header.

    Streaming responses don't flow through the middleware that uses parsers or renderers. As a
    result, the parser and renderer are only used to register supported 'Accept' headers.
    Instead of providing no-op renderer and parser classes, the views associated with the Docker
    registry use this custom content negotiation class.
    """

    def select_parser(self, request, parsers):
        """
        Select the first parser in the `.parser_classes` list.
        """
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix):
        """
        Select the first renderer in the `.renderer_classes` list.
        """
        return renderers[0], renderers[0].media_type


class VersionView(views.APIView):
    """
    APIView for Docker Registry v2 root.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """
        Return a response to the "GET" action.
        """
        return response.Response({})


class ServeContentMixin(object):
    """
    A mixin that helps serve content using the enabled web server.
    """

    def _django(self, path, headers):
        """
        The content web server is Django.

        Stream the bits.

        Args:
            path (str): The fully qualified path to the file to be served.
            headers (dict):

        Returns:
            StreamingHttpResponse: Stream the requested content.

        """
        try:
            file = FileWrapper(open(path, 'rb'))
        except FileNotFoundError:
            return HttpResponseNotFound()
        except PermissionError:
            return HttpResponseForbidden()
        file_response = StreamingHttpResponse(file)
        file_response['Content-Type'] = headers['Content-Type']
        file_response['Docker-Distribution-API-Version'] = 'registry/2.0'
        file_response['Content-Length'] = os.path.getsize(path)
        file_response['Content-Disposition'] = 'attachment; filename={n}'.format(
            n=os.path.basename(path))
        return file_response

    def _dispatch(self, path, headers):
        """
        Dispatch to the appropriate responder (method).

        Args:
            path (str): The fully qualified path to the file to be served.

        Returns:
            django.http.StreamingHttpResponse: on found.
            django.http.HttpResponseNotFound: on not-found.
            django.http.HttpResponseForbidden: on forbidden.
            django.http.HttpResponseRedirect: on redirect to the streamer.

        """
        server = settings.CONTENT['WEB_SERVER']

        try:
            responder = self.RESPONDER[server]
        except KeyError:
            raise ValueError(_('Web server "{t}" not supported.').format(t=server))
        else:
            return responder(self, path, headers)

    # Mapping of responder-method based on the type of web server.
    RESPONDER = {
        'django': _django,
    }


class TagView(views.APIView, ServeContentMixin):
    """
    APIView for Docker Registry v2 tag API.
    """

    authentication_classes = []
    permission_classes = []
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request, path, tag_name):
        """
        Return a response to the "GET" action.
        """
        distribution = get_object_or_404(DockerDistribution, base_path=path)
        try:
            ca = ContentArtifact.objects.get(
                content__in=distribution.publication.repository_version.content,
                relative_path=tag_name)
            content = ca.content.cast()
            if content.manifest:
                headers = {'Content-Type': content.manifest.media_type}
            else:
                headers = {'Content-Type': content.manifest_list.media_type}
        except ObjectDoesNotExist:
            pass
        else:
            artifact = ca.artifact
            if artifact:
                return self._dispatch(artifact.file.name, headers)
            else:
                raise ArtifactNotFound(path)

        raise PathNotResolved(path)


class BlobManifestView(views.APIView, ServeContentMixin):
    """
    APIView for Docker Registry v2 blob and manifest APIs.
    """

    authentication_classes = []
    permission_classes = []
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request, path, digest):
        """
        Return a response to the "GET" action.
        """
        distribution = get_object_or_404(DockerDistribution, base_path=path)
        try:
            ca = ContentArtifact.objects.get(
                content__in=distribution.publication.repository_version.content,
                relative_path=digest)
            headers = {'Content-Type': ca.content.cast().media_type}
        except ObjectDoesNotExist:
            pass
        else:
            artifact = ca.artifact
            if artifact:
                return self._dispatch(artifact.file.name, headers)
            else:
                raise ArtifactNotFound(path)

        raise PathNotResolved(path)


class TagsListView(views.APIView):
    """
    APIView for Docker Registry v2 tags/list API.
    """

    authentication_classes = []
    permission_classes = []
    content_negotiation_class = IgnoreClientContentNegotiation

    def get(self, request, path):
        """
        Return JSON of all tags in this repo.
        """
        distribution = get_object_or_404(DockerDistribution, base_path=path)
        tags = {'name': path, 'tags': []}
        for c in distribution.publication.repository_version.content:
            c = c.cast()
            if isinstance(c, Tag):
                tags['tags'].append(c.name)
        return response.Response(tags)
