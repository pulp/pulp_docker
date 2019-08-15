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
    url(r'docker/manifests/copy/$', ManifestCopyViewSet.as_view({'post': 'create'})),
    url(r'docker/recursive-add/$', RecursiveAdd.as_view({'post': 'create'})),
    url(r'docker/recursive-remove/$', RecursiveRemove.as_view({'post': 'create'})),
    url(r'docker/tag/$', TagImageViewSet.as_view({'post': 'create'})),
    url(r'docker/tags/copy/$', TagCopyViewSet.as_view({'post': 'create'})),
    url(r'docker/untag/$', UnTagImageViewSet.as_view({'post': 'create'}))
]
