from django.conf.urls import include, url
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'collections', views.CollectionViewSet, base_name='collections')
router.register(r'repositories', views.RepositoryViewSet, base_name='repositories')

urlpatterns = [
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^$', views.index, name='index'),
    url(r'^repositories/$', views.repositories, name="repositories"),
    url(r'^repositories/search/api/$', views.repositories_search_api, name="repositories_search_api"),
    url(r'^collections/$', views.collections, name="collections"),
    url(r'^collections/diff/$', views.collections_diff, name="collections_diff"),
    url(r'^collections/diff/api/(?P<path>.*)', views.collections_diff_api, name="collections_diff_api"),
    url(r'^collections/patch/$', views.collections_patch, name="collections_patch"),
    url(r'^collections/patch/api/(?P<collectionid>\d+)/(?P<patch_revision>.+)', views.collections_patch_api,
        name="collections_patch_api"),
    url(r'^collections/api/$', views.CollectionViewSet.as_view({'get': 'list'}), name="collections_api"),
    url(r'^collections/(?P<collectionid>\d+)/browse/$', views.collections_browse, name="collections_browse"),
    url(r'^collections/(?P<collectionid>\d+)/browse/api/(?P<path>.*)', views.collections_browse_api,
        name="collections_browse_api"),
    url(r'^tools/search/api/$', views.tools_search_api, name="tools_search_api"),
    url(r'^rest/', include(router.urls)),
]
