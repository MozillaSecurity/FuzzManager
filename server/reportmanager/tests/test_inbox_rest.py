"""Tests for Notifications rest api.

@author:     Eva Bardou

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import json
import logging

import pytest
import requests
from django.urls import reverse
from notifications.models import Notification
from notifications.signals import notify

from reportmanager.models import (
    OS,
    Bucket,
    Bug,
    BugProvider,
    Client,
    Platform,
    Product,
    ReportEntry,
    Tool,
)

LOG = logging.getLogger("fm.reportmanager.tests.inbox.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_notifications_no_auth(db, api_client, method):
    """must yield unauthorized without authentication"""
    assert (
        getattr(api_client, method)("/reportmanager/rest/inbox/", {}).status_code
        == requests.codes["unauthorized"]
    )


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.usefixtures("user_noperm")
def test_rest_notifications_no_perm(api_client, method):
    """must yield forbidden without permission"""
    assert (
        getattr(api_client, method)("/reportmanager/rest/inbox/", {}).status_code
        == requests.codes["forbidden"]
    )


@pytest.mark.parametrize(
    "method, url, user",
    [
        ("delete", "/reportmanager/rest/inbox/", "normal"),
        ("delete", "/reportmanager/rest/inbox/", "restricted"),
        ("patch", "/reportmanager/rest/inbox/", "normal"),
        ("patch", "/reportmanager/rest/inbox/", "restricted"),
        ("post", "/reportmanager/rest/inbox/", "normal"),
        ("post", "/reportmanager/rest/inbox/", "restricted"),
        ("put", "/reportmanager/rest/inbox/", "normal"),
        ("put", "/reportmanager/rest/inbox/", "restricted"),
    ],
    indirect=["user"],
)
def test_rest_notifications_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert (
        getattr(api_client, method)(url, {}).status_code
        == requests.codes["method_not_allowed"]
    )


@pytest.mark.parametrize(
    "method, url, user",
    [
        ("get", "/reportmanager/rest/inbox/1/", "normal"),
        ("get", "/reportmanager/rest/inbox/1/", "restricted"),
        ("delete", "/reportmanager/rest/inbox/1/", "normal"),
        ("delete", "/reportmanager/rest/inbox/1/", "restricted"),
        ("patch", "/reportmanager/rest/inbox/1/", "normal"),
        ("patch", "/reportmanager/rest/inbox/1/", "restricted"),
        ("post", "/reportmanager/rest/inbox/1/", "normal"),
        ("post", "/reportmanager/rest/inbox/1/", "restricted"),
        ("put", "/reportmanager/rest/inbox/1/", "normal"),
        ("put", "/reportmanager/rest/inbox/1/", "restricted"),
    ],
    indirect=["user"],
)
def test_rest_notifications_methods_not_found(api_client, user, method, url):
    """must yield not-found for undeclared methods"""
    assert (
        getattr(api_client, method)(url, {}).status_code == requests.codes["not_found"]
    )


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_notifications_list_unread(api_client, user, cm):
    """test that list returns the right notifications"""
    provider = BugProvider.objects.create(
        classname="BugzillaProvider", hostname="provider.com", urlTemplate="%s"
    )
    bug = Bug.objects.create(externalId="123456", externalType=provider)
    bucket = Bucket.objects.create(
        bug=bug,
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
        ),
    )
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    entry = ReportEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)

    notify.send(
        bug,
        description="Notification 1",
        level="info",
        recipient=user,
        target=bug,
        verb="inaccessible_bug",
    )
    notify.send(
        bucket,
        description="Notification 2",
        level="info",
        recipient=user,
        target=entry,
        verb="bucket_hit",
    )
    notify.send(
        bucket,
        description="Notification 3",
        level="info",
        recipient=user,
        target=entry,
        verb="bucket_hit",
    )
    n3 = Notification.objects.get(description="Notification 3")
    n3.unread = False
    n3.save()

    resp = api_client.get("/reportmanager/rest/inbox/")
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
    assert resp["results"] == [
        {
            "id": 2,
            "actor_url": reverse("reportmanager:sigview", kwargs={"sigid": bucket.id}),
            "data": None,
            "description": "Notification 2",
            "external_bug_url": None,
            "target_url": reverse(
                "reportmanager:reportview", kwargs={"reportid": entry.id}
            ),
            "verb": "bucket_hit",
        },
        {
            "id": 1,
            "actor_url": None,
            "data": None,
            "description": "Notification 1",
            "external_bug_url": f"https://{bug.externalType.hostname}/{bug.externalId}",
            "target_url": None,
            "verb": "inaccessible_bug",
        },
    ]


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_notifications_mark_as_read(api_client, user, cm):
    """test that mark_as_read only marks the targetted notification as read"""
    bucket = Bucket.objects.create(
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
        )
    )
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    entry = ReportEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)

    expected = 10
    [
        notify.send(
            bucket,
            recipient=user,
            actor=bucket,
            verb="bucket_hit",
            target=entry,
            level="info",
            description="Notification %d" % (i + 1),
        )
        for i in range(expected)
    ]
    notification = Notification.objects.first()

    resp = api_client.patch(
        f"/reportmanager/rest/inbox/{notification.id}/mark_as_read/"
    )
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
    bucket = Bucket.objects.create(
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
        )
    )
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    entry = ReportEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)

    expected = 10
    [
        notify.send(
            bucket,
            recipient=user,
            actor=bucket,
            verb="bucket_hit",
            target=entry,
            level="info",
            description="Notification %d" % (i + 1),
        )
        for i in range(expected)
    ]

    resp = api_client.patch("/reportmanager/rest/inbox/mark_all_as_read/")
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    assert Notification.objects.count() == expected
    for n in Notification.objects.all():
        assert not n.unread
