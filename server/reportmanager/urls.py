# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf.urls import include
from django.urls import re_path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"buckets", views.BucketViewSet, basename="buckets")
router.register(r"bugproviders", views.BugProviderViewSet, basename="bugproviders")
router.register(
    r"bugzilla/templates", views.BugzillaTemplateViewSet, basename="templates"
)
router.register(r"inbox", views.NotificationViewSet, basename="inbox")
router.register(r"reports", views.ReportEntryViewSet, basename="reports")

app_name = "reportmanager"
urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^bugprovider/$", views.bug_provider_list, name="bugproviders"),
    re_path(
        r"^bugprovider/(?P<provider_id>\d+)/$",
        views.bug_provider_view,
        name="bugproviderview",
    ),
    re_path(
        r"^bugprovider/(?P<provider_id>\d+)/delete/$",
        views.bug_provider_delete,
        name="bugproviderdel",
    ),
    re_path(
        r"^bugprovider/(?P<provider_id>\d+)/edit/$",
        views.bug_provider_edit,
        name="bugprovideredit",
    ),
    re_path(
        r"^bugprovider/create/$", views.bug_provider_create, name="bugprovidercreate"
    ),
    re_path(
        r"^bugzilla/templates/$",
        views.BugzillaTemplateListView.as_view(),
        name="templates",
    ),
    re_path(
        r"^bugzilla/templates/(?P<template_id>\d+)/$",
        views.BugzillaTemplateEditView.as_view(),
        name="templateedit",
    ),
    re_path(
        r"^bugzilla/templates/(?P<template_id>\d+)/delete/$",
        views.BugzillaTemplateDeleteView.as_view(),
        name="templatedel",
    ),
    re_path(
        r"^bugzilla/templates/(?P<template_id>\d+)/duplicate/$",
        views.bugzilla_template_duplicate,
        name="templatedup",
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
    re_path(r"^inbox/$", views.InboxView.as_view(), name="inbox"),
    re_path(r"^reports/$", views.report_list, name="reports"),
    re_path(r"^reports/(?P<report_id>\d+)/$", views.report_view, name="reportview"),
    re_path(
        r"^reports/(?P<report_id>\d+)/createbug/$",
        views.external_bug_create,
        name="createbug",
    ),
    re_path(
        r"^reports/(?P<report_id>\d+)/createbugcomment/$",
        views.external_bug_create_comment,
        name="createbugcomment",
    ),
    re_path(
        r"^reports/(?P<report_id>\d+)/delete/$", views.report_delete, name="reportdel"
    ),
    re_path(
        r"^reports/(?P<report_id>\d+)/edit/$", views.report_edit, name="reportedit"
    ),
    re_path(
        r"^reports/(?P<report_id>\d+)/findbuckets/$",
        views.signature_find,
        name="findbuckets",
    ),
    re_path(
        r"^rest/api-auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    re_path(
        r"^rest/reports/stats/$",
        views.ReportStatsViewSet.as_view({"get": "retrieve"}),
        name="report_stats_rest",
    ),
    re_path(
        r"^reports/watch/(?P<sigid>\d+)/$",
        views.bucket_watch_reports,
        name="bucketwatchreports",
    ),
    re_path(r"^settings/$", views.settings, name="settings"),
    re_path(r"^buckets/$", views.signature_list, name="buckets"),
    re_path(r"^buckets/(?P<sig_id>\d+)/$", views.signature_view, name="bucketview"),
    re_path(
        r"^buckets/(?P<sig_id>\d+)/delete/$", views.signature_delete, name="bucketdel"
    ),
    re_path(
        r"^buckets/(?P<sig_id>\d+)/edit/$", views.signature_edit, name="bucketedit"
    ),
    re_path(
        r"^buckets/(?P<sig_id>\d+)/try/(?P<report_id>\d+)/$",
        views.signature_try,
        name="buckettry",
    ),
    re_path(
        r"^buckets/(?P<sig_id>\d+)/optimize/$",
        views.signature_optimize,
        name="bucketopt",
    ),
    re_path(r"^buckets/watch/$", views.bucket_watch_list, name="bucketwatch"),
    re_path(
        r"^buckets/watch/(?P<sigid>\d+)/delete/$",
        views.bucket_watch_delete,
        name="bucketwatchdel",
    ),
    re_path(
        r"^buckets/watch/create/$", views.bucket_watch_create, name="createbucketwatch"
    ),
    re_path(r"^buckets/create/$", views.signature_create, name="createbucket"),
    re_path(r"^stats/$", views.stats, name="stats"),
    re_path(
        r"^usersettings/$", views.UserSettingsEditView.as_view(), name="usersettings"
    ),
    re_path(r"^rest/", include(router.urls)),
]
