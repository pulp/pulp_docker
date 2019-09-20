from django.conf.urls import url

from .viewsets import (
    ManifestCopyViewSet,
    RecursiveAdd,
    RecursiveRemove,
    TagCopyViewSet,
    TagImageViewSet,
    UnTagImageViewSet,
)


urlpatterns = [
    url(r'^pulp/api/v3/docker/manifests/copy/$', ManifestCopyViewSet.as_view({'post': 'create'})),
    url(r'^pulp/api/v3/docker/recursive-add/$', RecursiveAdd.as_view({'post': 'create'})),
    url(r'^pulp/api/v3/docker/recursive-remove/$', RecursiveRemove.as_view({'post': 'create'})),
    url(r'^pulp/api/v3/docker/tag/$', TagImageViewSet.as_view({'post': 'create'})),
    url(r'^pulp/api/v3/docker/tags/copy/$', TagCopyViewSet.as_view({'post': 'create'})),
    url(r'^pulp/api/v3/docker/untag/$', UnTagImageViewSet.as_view({'post': 'create'}))
]
