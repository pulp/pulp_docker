from django.conf.urls import url

from pulp_docker.app.views import (
    BlobManifestView,
    TagsListView,
    TagView,
    VersionView,
)

urlpatterns = [
    url(r'^v2/$', VersionView.as_view(), name='registry-root'),
    url(r'^v2/(?P<path>.+)/tags/list$', TagsListView.as_view()),
    url(r'^v2/(?P<path>.+)/manifests/(?P<digest>sha256:[A-Fa-f0-9]+)$',
        BlobManifestView.as_view()),
    url(r'^v2/(?P<path>.+)/manifests/(?P<tag_name>[A-Za-z0-9\._-]+)$',
        TagView.as_view()),
    url(r'^v2/(?P<path>.+)/blobs/(?P<digest>sha256:[A-Fa-f0-9]+)$',
        BlobManifestView.as_view())
]
