from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"collections", views.CollectionViewSet, basename="collections")
router.register(r"repositories", views.RepositoryViewSet, basename="repositories")
router.register(
    r"reportconfigurations",
    views.ReportConfigurationViewSet,
    basename="reportconfigurations",
)


app_name = "covmanager"
urlpatterns = [
    re_path(
        r"^rest/api-auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    re_path(r"^$", views.index, name="index"),
    re_path(r"^reports/$", views.reports, name="reports"),
    re_path(
        r"^reports/api/$",
        views.ReportViewSet.as_view({"get": "list"}),
        name="reports_api",
    ),
    re_path(
        r"^reports/api/update/(?P<pk>\d+)/$",
        views.ReportViewSet.as_view({"post": "partial_update"}),
        name="reports_update_api",
    ),
    re_path(r"^repositories/$", views.repositories, name="repositories"),
    re_path(
        r"^repositories/search/api/$",
        views.repositories_search_api,
        name="repositories_search_api",
    ),
    re_path(r"^collections/$", views.collections, name="collections"),
    re_path(
        r"^collections/aggregate/api/",
        views.collections_aggregate_api,
        name="collections_aggregate_api",
    ),
    re_path(r"^collections/diff/$", views.collections_diff, name="collections_diff"),
    re_path(
        r"^collections/diff/api/(?P<path>.*)",
        views.collections_diff_api,
        name="collections_diff_api",
    ),
    re_path(
        r"^collections/(?P<collectionid>\d+)/download/$",
        views.collections_download,
        name="collections_download",
    ),
    re_path(r"^collections/patch/$", views.collections_patch, name="collections_patch"),
    re_path(
        r"^collections/patch/api/(?P<collectionid>\d+)/(?P<patch_revision>.+)",
        views.collections_patch_api,
        name="collections_patch_api",
    ),
    re_path(
        r"^collections/api/$",
        views.CollectionViewSet.as_view({"get": "list"}),
        name="collections_api",
    ),
    re_path(
        r"^collections/(?P<collectionid>\d+)/browse/$",
        views.collections_browse,
        name="collections_browse",
    ),
    re_path(
        r"^collections/(?P<collectionid>\d+)/browse/api/(?P<path>.*)",
        views.collections_browse_api,
        name="collections_browse_api",
    ),
    re_path(
        r"^collections/(?P<collectionid>\d+)/summary/$",
        views.collections_reportsummary,
        name="collections_reportsummary",
    ),
    re_path(
        r"^collections/(?P<collectionid>\d+)/summary/api/",
        views.collections_reportsummary_api,
        name="collections_reportsummary_api",
    ),
    re_path(
        r"^collections/(?P<collectionid>\d+)/summary/htmlexport/$",
        views.collections_reportsummary_html_list,
        name="collections_reportsummary_html_list",
    ),
    re_path(
        r"^reportconfigurations/$",
        views.reportconfigurations,
        name="reportconfigurations",
    ),
    re_path(
        r"^reportconfigurations/api/$",
        views.ReportConfigurationViewSet.as_view({"get": "list"}),
        name="reportconfigurations_list_api",
    ),
    re_path(
        r"^reportconfigurations/api/create/$",
        views.ReportConfigurationViewSet.as_view({"post": "create"}),
        name="reportconfigurations_create_api",
    ),
    re_path(
        r"^reportconfigurations/api/update/(?P<pk>\d+)/$",
        views.ReportConfigurationViewSet.as_view({"post": "partial_update"}),
        name="reportconfigurations_update_api",
    ),
    re_path(r"^tools/search/api/$", views.tools_search_api, name="tools_search_api"),
    re_path(r"^rest/", include(router.urls)),
]
