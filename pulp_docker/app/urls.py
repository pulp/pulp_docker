from django.conf.urls import url

from .viewsets import RecursiveAdd, TagImageViewSet, UnTagImageViewSet


urlpatterns = [
    url(r'docker/recursive-add/$', RecursiveAdd.as_view({'post': 'create'})),
    url(r'docker/tag/$', TagImageViewSet.as_view({'post': 'create'})),
    url(r'docker/untag/$', UnTagImageViewSet.as_view({'post': 'create'}))
]
