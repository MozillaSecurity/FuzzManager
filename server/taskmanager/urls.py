from django.conf.urls import include, url
from rest_framework import routers
from . import views


router = routers.DefaultRouter()
router.register(r"pools", views.PoolViewSet)
router.register(r"tasks", views.TaskViewSet)


app_name = "taskmanager"
urlpatterns = [
    url(r"^rest/api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"^$", views.index, name="index"),
    url(r"^pools/$", views.list_pools, name="pool-list-ui"),
    url(r"^pools/(?P<pk>\d+)/$", views.view_pool, name="pool-view-ui"),
    url(r"^rest/", include(router.urls)),
]
