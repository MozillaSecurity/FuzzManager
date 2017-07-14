from django.conf.urls import patterns, include, url
import os
from rest_framework import routers

from covmanager import views
from server import settings


router = routers.DefaultRouter()
router.register(r'collections', views.CollectionViewSet, base_name='collections')

urlpatterns = patterns('',
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^rest/', include(router.urls)),
