from django.conf.urls import patterns, include, url
from rest_framework import routers
from crashmanager import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()

router = routers.DefaultRouter()
router.register(r'signatures', views.BucketViewSet)
router.register(r'crashes', views.CrashEntryViewSet)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'server.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^crashmanager/', include('crashmanager.urls', namespace="crashmanager")),
)

urlpatterns += staticfiles_urlpatterns()