from django.conf.urls import patterns, include, url
import os
from rest_framework import routers

from covmanager import views
from server import settings

router = routers.DefaultRouter()
router.register(r'collections', views.CollectionViewSet, base_name='collections')
router.register(r'repositories', views.RepositoryViewSet, base_name='repositories')

urlpatterns = patterns('',
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^repositories/', views.repositories, name="repositories"),
    url(r'^collections/', views.collections, name="collections"),
    url(r'^collections/(?P<collectionid>\d+)/src/(?P<path>.*)', views.getRawCoverageSourceData),
    url(r'^rest/', include(router.urls)),
)
