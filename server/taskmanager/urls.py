from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"pools", views.PoolViewSet)
router.register(r"tasks", views.TaskViewSet)


app_name = "taskmanager"
urlpatterns = [
    re_path(
        r"^rest/api-auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    re_path(r"^$", views.index, name="index"),
    re_path(r"^pools/$", views.list_pools, name="pool-list-ui"),
    re_path(r"^pools/(?P<pk>\d+)/$", views.view_pool, name="pool-view-ui"),
    re_path(r"^rest/", include(router.urls)),
]
