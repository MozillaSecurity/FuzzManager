from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"op", views.AsyncOpViewSet, basename="op")
router.register(r"reports", views.ReportEntryViewSet, basename="reports")
router.register(r"buckets", views.BucketViewSet, basename="buckets")
router.register(r"bugproviders", views.BugProviderViewSet, basename="bugproviders")
router.register(
    r"bugzilla/templates", views.BugzillaTemplateViewSet, basename="templates"
)
router.register(r"inbox", views.NotificationViewSet, basename="inbox")


app_name = "reportmanager"
urlpatterns = [
    re_path(
        r"^rest/api-auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    re_path(
        r"^rest/reports/stats/$",
        views.ReportStatsViewSet.as_view({"get": "retrieve"}),
        name="report_stats_rest",
    ),
    re_path(r"^$", views.index, name="index"),
    re_path(r"^signatures/$", views.signatures, name="signatures"),
    re_path(r"^signatures/new/$", views.newSignature, name="signew"),
    re_path(r"^signatures/(?P<sigid>\d+)/edit/$", views.editSignature, name="sigedit"),
    re_path(
        r"^signatures/(?P<sigid>\d+)/try/(?P<reportid>\d+)/$",
        views.trySignature,
        name="sigtry",
    ),
    re_path(
        r"^signatures/(?P<sigid>\d+)/optimize/$", views.optimizeSignature, name="sigopt"
    ),
    re_path(
        r"^signatures/(?P<sigid>\d+)/preoptimized/$",
        views.optimizeSignaturePrecomputed,
        name="sigoptpre",
    ),
    re_path(r"^signatures/(?P<sigid>\d+)/$", views.viewSignature, name="sigview"),
    re_path(
        r"^signatures/(?P<sigid>\d+)/delete/$", views.deleteSignature, name="sigdel"
    ),
    re_path(r"^signatures/watch/$", views.watchedSignatures, name="sigwatch"),
    re_path(
        r"^signatures/watch/(?P<sigid>\d+)/delete/$",
        views.deleteBucketWatch,
        name="sigwatchdel",
    ),
    re_path(r"^signatures/watch/new/$", views.newBucketWatch, name="sigwatchnew"),
    re_path(r"^reports/$", views.reports, name="reports"),
    re_path(
        r"^reports/watch/(?P<sigid>\d+)/$",
        views.bucketWatchReports,
        name="sigwatchreports",
    ),
    re_path(r"^reports/(?P<reportid>\d+)/$", views.viewReportEntry, name="reportview"),
    re_path(
        r"^reports/(?P<reportid>\d+)/edit/$", views.editReportEntry, name="reportedit"
    ),
    re_path(
        r"^reports/(?P<reportid>\d+)/delete/$",
        views.deleteReportEntry,
        name="reportdel",
    ),
    re_path(
        r"^reports/(?P<reportid>\d+)/createbug/$",
        views.createExternalBug,
        name="createbug",
    ),
    re_path(
        r"^reports/(?P<reportid>\d+)/createbugcomment/$",
        views.createExternalBugComment,
        name="createbugcomment",
    ),
    re_path(
        r"^reports/(?P<reportid>\d+)/findsignatures/$",
        views.findSignatures,
        name="findsigs",
    ),
    re_path(r"^bugprovider/$", views.viewBugProviders, name="bugproviders"),
    re_path(
        r"^bugprovider/create/$", views.createBugProvider, name="bugprovidercreate"
    ),
    re_path(
        r"^bugprovider/(?P<providerId>\d+)/$",
        views.viewBugProvider,
        name="bugproviderview",
    ),
    re_path(
        r"^bugprovider/(?P<providerId>\d+)/edit/$",
        views.editBugProvider,
        name="bugprovideredit",
    ),
    re_path(
        r"^bugprovider/(?P<providerId>\d+)/delete/$",
        views.deleteBugProvider,
        name="bugproviderdel",
    ),
    re_path(
        r"^bugzilla/templates/$",
        views.BugzillaTemplateListView.as_view(),
        name="templates",
    ),
    re_path(
        r"^bugzilla/templates/create-bug/$",
        views.BugzillaTemplateBugCreateView.as_view(),
        name="templatecreatebug",
    ),
    re_path(
        r"^bugzilla/templates/create-comment/$",
        views.BugzillaTemplateCommentCreateView.as_view(),
        name="templatecreatecomment",
    ),
    re_path(
        r"^bugzilla/templates/(?P<templateId>\d+)/$",
        views.BugzillaTemplateEditView.as_view(),
        name="templateedit",
    ),
    re_path(
        r"^bugzilla/templates/(?P<templateId>\d+)/duplicate/$",
        views.duplicateBugzillaTemplate,
        name="templatedup",
    ),
    re_path(
        r"^bugzilla/templates/(?P<templateId>\d+)/delete/$",
        views.BugzillaTemplateDeleteView.as_view(),
        name="templatedel",
    ),
    re_path(r"^stats/$", views.stats, name="stats"),
    re_path(r"^settings/$", views.settings, name="settings"),
    re_path(
        r"^usersettings/$", views.UserSettingsEditView.as_view(), name="usersettings"
    ),
    re_path(r"^inbox/$", views.InboxView.as_view(), name="inbox"),
    re_path(r"^rest/", include(router.urls)),
]
