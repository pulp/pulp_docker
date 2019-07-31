from django.conf.urls import url

from .viewsets import TagImageViewSet, UnTagImageViewSet


urlpatterns = [
    url(r'docker/tag/$', TagImageViewSet.as_view({'post': 'create'})),
    url(r'docker/untag/$', UnTagImageViewSet.as_view({'post': 'create'}))
]
