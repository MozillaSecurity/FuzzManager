from django.conf.urls import patterns, include, url
from rest_framework import routers
from crashmanager import views

router = routers.DefaultRouter()
router.register(r'signatures', views.BucketViewSet)
router.register(r'crashes', views.CrashEntryViewSet)

urlpatterns = patterns('',
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^$', views.index, name='index'),
    url(r'^signatures/$', views.signatures, name='signatures'),
    url(r'^signatures/new/$', views.newSignature, name='signew'),
    url(r'^signatures/(?P<sigid>\d+)/edit/$', views.editSignature, name='sigedit'),
    url(r'^signatures/(?P<sigid>\d+)/linkextbug/$', views.editSignature, name='linkextbug'),
    url(r'^signatures/(?P<sigid>\d+)/view/$', views.viewSignature, name='sigview'),
    url(r'^signatures/(?P<sigid>\d+)/delete/$', views.deleteSignature, name='sigdel'),
    url(r'^crashes/$', views.crashes, name='crashes'),
    url(r'^crashes/(?P<crashid>\d+)/$', views.viewCrashEntry, name='crashview'),
    url(r'^rest/', include(router.urls)),
)