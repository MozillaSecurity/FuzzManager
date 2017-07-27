from django.conf.urls import patterns, include, url
from rest_framework import routers

from covmanager import views

router = routers.DefaultRouter()
router.register(r'collections', views.CollectionViewSet, base_name='collections')
router.register(r'repositories', views.RepositoryViewSet, base_name='repositories')

urlpatterns = patterns('',
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^$', views.index, name='index'),
    url(r'^repositories/', views.repositories, name="repositories"),
    url(r'^collections/$', views.collections, name="collections"),
    url(r'^collections/api/$', views.CollectionViewSet.as_view({'get': 'list'}), name="collections_api"),
    url(r'^collections/(?P<collectionid>\d+)/browse/$', views.collections_browse, name="collections_browse"),
    url(r'^collections/(?P<collectionid>\d+)/browse/api/(?P<path>.*)', views.collections_browse_api, name="collections_browse_api"),
    url(r'^rest/', include(router.urls)),
)
