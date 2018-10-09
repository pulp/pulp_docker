from django.conf.urls import url

from pulp_docker.app.views import (
    VersionView
)

urlpatterns = [
    url(r'^v2/$', VersionView.as_view()),
]
