# coding: utf-8
"""Tests for Notifications rest api.

@author:     Eva Bardou

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
from __future__ import unicode_literals
from django.urls import reverse
from notifications.models import Notification
from notifications.signals import notify
import json
import logging
import pytest
import requests
from crashmanager.models import Bucket, Bug, BugProvider, Client, CrashEntry, OS, Platform, \
    Product, Tool


LOG = logging.getLogger("fm.crashmanager.tests.inbox.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_notifications_no_auth(db, api_client, method):
    """must yield unauthorized without authentication"""
    assert getattr(api_client, method)(
        "/crashmanager/rest/inbox/", {}
    ).status_code == requests.codes["unauthorized"]


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_notifications_no_perm(user_noperm, api_client, method):
    """must yield forbidden without permission"""
    assert getattr(api_client, method)(
        "/crashmanager/rest/inbox/", {}
    ).status_code == requests.codes["forbidden"]


@pytest.mark.parametrize("method, url, user", [
    ("delete", "/crashmanager/rest/inbox/", "normal"),
    ("delete", "/crashmanager/rest/inbox/", "restricted"),
    ("patch", "/crashmanager/rest/inbox/", "normal"),
    ("patch", "/crashmanager/rest/inbox/", "restricted"),
    ("post", "/crashmanager/rest/inbox/", "normal"),
    ("post", "/crashmanager/rest/inbox/", "restricted"),
    ("put", "/crashmanager/rest/inbox/", "normal"),
    ("put", "/crashmanager/rest/inbox/", "restricted"),
], indirect=["user"])
def test_rest_notifications_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes["method_not_allowed"]


@pytest.mark.parametrize("method, url, user", [
    ("get", "/crashmanager/rest/inbox/1/", "normal"),
    ("get", "/crashmanager/rest/inbox/1/", "restricted"),
    ("delete", "/crashmanager/rest/inbox/1/", "normal"),
    ("delete", "/crashmanager/rest/inbox/1/", "restricted"),
    ("patch", "/crashmanager/rest/inbox/1/", "normal"),
    ("patch", "/crashmanager/rest/inbox/1/", "restricted"),
    ("post", "/crashmanager/rest/inbox/1/", "normal"),
    ("post", "/crashmanager/rest/inbox/1/", "restricted"),
    ("put", "/crashmanager/rest/inbox/1/", "normal"),
    ("put", "/crashmanager/rest/inbox/1/", "restricted"),
], indirect=["user"])
def test_rest_notifications_methods_not_found(api_client, user, method, url):
    """must yield not-found for undeclared methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes["not_found"]


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_notifications_list_unread(api_client, user, cm):
    """test that list returns the right notifications"""
    provider = BugProvider.objects.create(classname="BugzillaProvider",
                                          hostname="provider.com",
                                          urlTemplate="%s")
    bug = Bug.objects.create(externalId="123456", externalType=provider)
    bucket = Bucket.objects.create(bug=bug, signature=json.dumps(
        {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
    ))
    defaults = {"client": Client.objects.create(),
                "os": OS.objects.create(),
                "platform": Platform.objects.create(),
                "product": Product.objects.create(),
                "tool": Tool.objects.create()}
    entry = CrashEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)

    notify.send(bug, recipient=user, actor=bug, verb="inaccessible_bug",
                target=bug, level="info", description="Notification 1")
    notify.send(bucket, recipient=user, actor=bucket, verb="bucket_hit",
                target=entry, level="info", description="Notification 2")
    notify.send(bucket, recipient=user, actor=bucket, verb="bucket_hit",
                target=entry, level="info", description="Notification 3")
    n3 = Notification.objects.get(description="Notification 3")
    n3.unread = False
    n3.save()

    resp = api_client.get("/crashmanager/rest/inbox/")
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = resp.json()
    assert set(resp) == {"count", "next", "previous", "results"}
    assert resp["count"] == 2
    assert resp["next"] is None
    assert resp["previous"] is None
    assert len(resp["results"]) == 2
    # Popping out timestamps
    for r in resp["results"]:
        del r["timestamp"]
    assert resp["results"] == [{
        "id": 2,
        "actor_url": reverse("crashmanager:sigview", kwargs={"sigid": bucket.id}),
        "description": "Notification 2",
        "external_bug_url": None,
        "target_url": reverse("crashmanager:crashview", kwargs={"crashid": entry.id}),
        "verb": "bucket_hit"
    }, {
        "id": 1,
        "actor_url": None,
        "description": "Notification 1",
        "external_bug_url": f"https://{bug.externalType.hostname}/{bug.externalId}",
        "target_url": None,
        "verb": "inaccessible_bug"
    }]


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_notifications_mark_as_read(api_client, user, cm):
    """test that mark_as_read only marks the targetted notification as read"""
    bucket = Bucket.objects.create(signature=json.dumps(
        {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
    ))
    defaults = {"client": Client.objects.create(),
                "os": OS.objects.create(),
                "platform": Platform.objects.create(),
                "product": Product.objects.create(),
                "tool": Tool.objects.create()}
    entry = CrashEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)

    expected = 10
    [notify.send(bucket, recipient=user, actor=bucket, verb="bucket_hit",
                 target=entry, level="info", description="Notification %d" % (i + 1))
     for i in range(expected)]
    notification = Notification.objects.first()

    resp = api_client.patch(f"/crashmanager/rest/inbox/{notification.id}/mark_as_read/")
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    assert Notification.objects.count() == expected
    for n in Notification.objects.all():
        if n.id == notification.id:
            assert not n.unread
        else:
            assert n.unread


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_notifications_mark_all_as_read(api_client, user, cm):
    """test that mark_all_as_read marks all user notifications as read"""
    bucket = Bucket.objects.create(signature=json.dumps(
        {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
    ))
    defaults = {"client": Client.objects.create(),
                "os": OS.objects.create(),
                "platform": Platform.objects.create(),
                "product": Product.objects.create(),
                "tool": Tool.objects.create()}
    entry = CrashEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)

    expected = 10
    [notify.send(bucket, recipient=user, actor=bucket, verb="bucket_hit",
                 target=entry, level="info", description="Notification %d" % (i + 1))
     for i in range(expected)]

    resp = api_client.patch("/crashmanager/rest/inbox/mark_all_as_read/")
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    assert Notification.objects.count() == expected
    for n in Notification.objects.all():
        assert not n.unread
