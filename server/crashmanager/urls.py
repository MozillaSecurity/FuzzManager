from django.conf.urls import include, url
from rest_framework import routers
from . import views


router = routers.DefaultRouter()
router.register(r'crashes', views.CrashEntryViewSet, basename='crashes')
router.register(r'buckets', views.BucketViewSet, basename='buckets')
router.register(r'bugproviders', views.BugProviderViewSet, basename='bugproviders')
router.register(r'bugzilla/templates', views.BugzillaTemplateViewSet, basename='templates')
router.register(r'inbox', views.NotificationViewSet, basename='inbox')


app_name = 'crashmanager'
urlpatterns = [
    url(r'^rest/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^rest/signatures/download/$', views.SignaturesDownloadView.as_view(), name='download_signatures_rest'),
    url(r'^rest/crashes/(?P<crashid>\d+)/download/$', views.TestDownloadView.as_view(), name='download_test_rest'),
    url(r'^$', views.index, name='index'),
    url(r'^signatures/$', views.signatures, name='signatures'),
    url(r'^signatures/download/$', views.SignaturesDownloadView.as_view(), name='download_signatures'),
    url(r'^signatures/new/$', views.newSignature, name='signew'),
    url(r'^signatures/(?P<sigid>\d+)/edit/$', views.editSignature, name='sigedit'),
    url(r'^signatures/(?P<sigid>\d+)/try/(?P<crashid>\d+)/$', views.trySignature, name='sigtry'),
    url(r'^signatures/(?P<sigid>\d+)/optimize/$', views.optimizeSignature, name='sigopt'),
    url(r'^signatures/(?P<sigid>\d+)/preoptimized/$', views.optimizeSignaturePrecomputed, name='sigoptpre'),
    url(r'^signatures/(?P<sigid>\d+)/$', views.viewSignature, name='sigview'),
    url(r'^signatures/(?P<sigid>\d+)/delete/$', views.deleteSignature, name='sigdel'),
    url(r'^signatures/watch/$', views.watchedSignatures, name='sigwatch'),
    url(r'^signatures/watch/(?P<sigid>\d+)/delete/$', views.deleteBucketWatch, name='sigwatchdel'),
    url(r'^signatures/watch/new/$', views.newBucketWatch, name='sigwatchnew'),
    url(r'^crashes/$', views.crashes, name='crashes'),
    url(r'^crashes/watch/(?P<sigid>\d+)/$', views.bucketWatchCrashes, name='sigwatchcrashes'),
    url(r'^crashes/(?P<crashid>\d+)/$', views.viewCrashEntry, name='crashview'),
    url(r'^crashes/(?P<crashid>\d+)/edit/$', views.editCrashEntry, name='crashedit'),
    url(r'^crashes/(?P<crashid>\d+)/delete/$', views.deleteCrashEntry, name='crashdel'),
    url(r'^crashes/(?P<crashid>\d+)/createbug/$', views.createExternalBug, name='createbug'),
    url(r'^crashes/(?P<crashid>\d+)/createbugcomment/$', views.createExternalBugComment, name='createbugcomment'),
    url(r'^crashes/(?P<crashid>\d+)/findsignatures/$', views.findSignatures, name='findsigs'),
    url(r'^crashes/(?P<crashid>\d+)/download/$', views.TestDownloadView.as_view(), name='download_test'),
    url(r'^bugprovider/$', views.viewBugProviders, name='bugproviders'),
    url(r'^bugprovider/create/$', views.createBugProvider, name='bugprovidercreate'),
    url(r'^bugprovider/(?P<providerId>\d+)/$', views.viewBugProvider, name='bugproviderview'),
    url(r'^bugprovider/(?P<providerId>\d+)/edit/$', views.editBugProvider, name='bugprovideredit'),
    url(r'^bugprovider/(?P<providerId>\d+)/delete/$', views.deleteBugProvider, name='bugproviderdel'),
    url(r'^bugzilla/templates/$', views.BugzillaTemplateListView.as_view(), name='templates'),
    url(r'^bugzilla/templates/create-bug/$', views.BugzillaTemplateBugCreateView.as_view(), name='templatecreatebug'),
    url(r'^bugzilla/templates/create-comment/$', views.BugzillaTemplateCommentCreateView.as_view(),
        name='templatecreatecomment'),
    url(r'^bugzilla/templates/(?P<templateId>\d+)/$', views.BugzillaTemplateEditView.as_view(), name='templateedit'),
    url(r'^bugzilla/templates/(?P<templateId>\d+)/duplicate/$', views.duplicateBugzillaTemplate, name='templatedup'),
    url(r'^bugzilla/templates/(?P<templateId>\d+)/delete/$', views.BugzillaTemplateDeleteView.as_view(),
        name='templatedel'),

    url(r'^stats/$', views.stats, name='stats'),
    url(r'^settings/$', views.settings, name='settings'),
    url(r'^usersettings/$', views.UserSettingsEditView.as_view(), name='usersettings'),
    url(r'^inbox/$', views.InboxView.as_view(), name='inbox'),

    url(r'^rest/', include(router.urls)),
]
