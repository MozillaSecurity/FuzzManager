from django.conf.urls import include, url
from rest_framework import routers
from . import views


router = routers.DefaultRouter()
router.register(r'collections', views.CollectionViewSet, basename='collections')
router.register(r'repositories', views.RepositoryViewSet, basename='repositories')
router.register(r'reportconfigurations', views.ReportConfigurationViewSet, basename='reportconfigurations')


app_name = 'covmanager'
urlpatterns = [
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^$', views.index, name='index'),
    url(r'^reports/$', views.reports, name="reports"),
    url(r'^reports/api/$', views.ReportViewSet.as_view({'get': 'list'}), name="reports_api"),
    url(r'^reports/api/update/(?P<pk>\d+)/$', views.ReportViewSet.as_view({'post': 'partial_update'}),
        name="reports_update_api"),
    url(r'^repositories/$', views.repositories, name="repositories"),
    url(r'^repositories/search/api/$', views.repositories_search_api, name="repositories_search_api"),
    url(r'^collections/$', views.collections, name="collections"),
    url(r'^collections/aggregate/api/', views.collections_aggregate_api, name="collections_aggregate_api"),
    url(r'^collections/diff/$', views.collections_diff, name="collections_diff"),
    url(r'^collections/diff/api/(?P<path>.*)', views.collections_diff_api, name="collections_diff_api"),
    url(r'^collections/(?P<collectionid>\d+)/download/$', views.collections_download, name="collections_download"),
    url(r'^collections/patch/$', views.collections_patch, name="collections_patch"),
    url(r'^collections/patch/api/(?P<collectionid>\d+)/(?P<patch_revision>.+)', views.collections_patch_api,
        name="collections_patch_api"),
    url(r'^collections/api/$', views.CollectionViewSet.as_view({'get': 'list'}), name="collections_api"),
    url(r'^collections/(?P<collectionid>\d+)/browse/$', views.collections_browse, name="collections_browse"),
    url(r'^collections/(?P<collectionid>\d+)/browse/api/(?P<path>.*)', views.collections_browse_api,
        name="collections_browse_api"),
    url(r'^collections/(?P<collectionid>\d+)/summary/$', views.collections_reportsummary,
        name="collections_reportsummary"),
    url(r'^collections/(?P<collectionid>\d+)/summary/api/', views.collections_reportsummary_api,
        name="collections_reportsummary_api"),
    url(r'^collections/(?P<collectionid>\d+)/summary/htmlexport/$', views.collections_reportsummary_html_list,
        name="collections_reportsummary_html_list"),
    url(r'^reportconfigurations/$', views.reportconfigurations, name="reportconfigurations"),
    url(r'^reportconfigurations/api/$', views.ReportConfigurationViewSet.as_view({'get': 'list'}),
        name="reportconfigurations_list_api"),
    url(r'^reportconfigurations/api/create/$', views.ReportConfigurationViewSet.as_view({'post': 'create'}),
        name="reportconfigurations_create_api"),
    url(r'^reportconfigurations/api/update/(?P<pk>\d+)/$',
        views.ReportConfigurationViewSet.as_view({'post': 'partial_update'}),
        name="reportconfigurations_update_api"),
    url(r'^tools/search/api/$', views.tools_search_api, name="tools_search_api"),
    url(r'^rest/', include(router.urls)),
]
