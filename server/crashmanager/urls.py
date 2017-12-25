from django.conf.urls import include, url
from django.views.static import serve
import os
from rest_framework import routers

from crashmanager import views
from server import settings


router = routers.DefaultRouter()
router.register(r'crashes', views.CrashEntryViewSet, base_name='crashes')
router.register(r'buckets', views.BucketViewSet, base_name='buckets')

urlpatterns = [
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^logout/$', views.logout_view, name='logout'),
    url(r'^$', views.index, name='index'),
    url(r'^signatures/$', views.signatures, name='signatures'),
    url(r'^signatures/all/$', views.allSignatures, name='allsignatures'),
    url(r'^signatures/new/$', views.newSignature, name='signew'),
    url(r'^signatures/(?P<sigid>\d+)/edit/$', views.editSignature, name='sigedit'),
    url(r'^signatures/(?P<sigid>\d+)/link/$', views.linkSignature, name='siglink'),
    url(r'^signatures/(?P<sigid>\d+)/unlink/$', views.unlinkSignature, name='sigunlink'),
    url(r'^signatures/(?P<sigid>\d+)/try/(?P<crashid>\d+)/$', views.trySignature, name='sigtry'),
    url(r'^signatures/(?P<sigid>\d+)/optimize/$', views.optimizeSignature, name='sigopt'),
    url(r'^signatures/(?P<sigid>\d+)/$', views.viewSignature, name='sigview'),
    url(r'^signatures/(?P<sigid>\d+)/delete/$', views.deleteSignature, name='sigdel'),
    url(r'^signatures/watch/$', views.watchedSignatures, name='sigwatch'),
    url(r'^signatures/watch/(?P<sigid>\d+)/delete/$', views.deleteBucketWatch, name='sigwatchdel'),
    url(r'^signatures/watch/new/$', views.newBucketWatch, name='sigwatchnew'),
    url(r'^crashes/$', views.crashes, name='crashes'),
    url(r'^crashes/all/$', views.crashes, name='allcrashes', kwargs={'ignore_toolfilter': True}),
    url(r'^crashes/query/$', views.queryCrashes, name='querycrashes'),
    url(r'^crashes/watch/(?P<sigid>\d+)/$', views.bucketWatchCrashes, name='sigwatchcrashes'),
    url(r'^crashes/autoassign/$', views.autoAssignCrashEntries, name='autoassign'),
    url(r'^crashes/(?P<crashid>\d+)/$', views.viewCrashEntry, name='crashview'),
    url(r'^crashes/(?P<crashid>\d+)/edit/$', views.editCrashEntry, name='crashedit'),
    url(r'^crashes/(?P<crashid>\d+)/delete/$', views.deleteCrashEntry, name='crashdel'),
    url(r'^crashes/(?P<crashid>\d+)/createbug/$', views.createExternalBug, name='createbug'),
    url(r'^crashes/(?P<crashid>\d+)/createbugcomment/$', views.createExternalBugComment, name='createbugcomment'),
    url(r'^crashes/(?P<crashid>\d+)/findsignatures/$', views.findSignatures, name='findsigs'),
    url(r'^bugprovider/$', views.viewBugProviders, name='bugproviders'),
    url(r'^bugprovider/create/$', views.createBugProvider, name='bugprovidercreate'),
    url(r'^bugprovider/(?P<providerId>\d+)/$', views.viewBugProvider, name='bugproviderview'),
    url(r'^bugprovider/(?P<providerId>\d+)/edit/$', views.editBugProvider, name='bugprovideredit'),
    url(r'^bugprovider/(?P<providerId>\d+)/delete/$', views.deleteBugProvider, name='bugproviderdel'),
    url(r'^bugprovider/(?P<providerId>\d+)/templates/create/$', views.createBugTemplate, name='createtemplate'),
    url(r'^bugprovider/(?P<providerId>\d+)/templates/(?P<templateId>\d+)/$', views.viewEditBugTemplate,
        name='viewtemplate', kwargs={'mode': 'create'}),
    url(r'^bugprovider/(?P<providerId>\d+)/templates/(?P<templateId>\d+)/comment/$', views.viewEditBugTemplate,
        name='viewcommenttemplate', kwargs={'mode': 'comment'}),

    url(r'^stats/$', views.stats, name='stats'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^usersettings/$', views.userSettings, name='usersettings'),

    url(r'^rest/', include(router.urls)),
]

# This makes Django serve our testcases from the tests/ URL. When hosting this
# project in production, one should consider serving tests directly through
# the webserver rather than through Django for performance reasons.
urlpatterns += [url(r'^tests/(.*)$', serve, name='download',
                    kwargs={'document_root': os.path.join(settings.BASE_DIR, 'tests')})]
