"""Tests for ReportManager triage_new_reports management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import json

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from notifications.models import Notification

from reportmanager.models import (
    OS,
    Bucket,
    BucketWatch,
    Client,
    Platform,
    Product,
    ReportEntry,
    Tool,
)
from reportmanager.models import User as cmUser

pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("reportmanager_test")


def test_args():
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("triage_new_reports", "")


def test_none():
    call_command("triage_new_reports")


def test_some():
    buckets = [
        Bucket.objects.create(
            signature=json.dumps(
                {"symptoms": [{"src": "stderr", "type": "output", "value": "/foo/"}]}
            )
        ),
        Bucket.objects.create(
            signature=json.dumps(
                {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
            )
        ),
    ]
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    reports = [
        ReportEntry.objects.create(bucket=buckets[0], rawStderr="match", **defaults),
        ReportEntry.objects.create(rawStderr="match", **defaults),
        ReportEntry.objects.create(rawStderr="blah", **defaults),
    ]
    for c in reports:
        assert not c.triagedOnce

    call_command("triage_new_reports")

    reports = [ReportEntry.objects.get(pk=c.pk) for c in reports]

    for c in reports:
        assert c.triagedOnce

    assert reports[0].bucket.pk == buckets[0].pk
    assert reports[1].bucket.pk == buckets[1].pk
    assert reports[2].bucket is None


def test_some_with_notification():
    buckets = [
        Bucket.objects.create(
            signature=json.dumps(
                {"symptoms": [{"src": "stderr", "type": "output", "value": "/foo/"}]}
            )
        ),
        Bucket.objects.create(
            signature=json.dumps(
                {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
            )
        ),
    ]
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    reports = [
        ReportEntry.objects.create(bucket=buckets[0], rawStderr="match", **defaults),
        ReportEntry.objects.create(rawStderr="match", **defaults),
        ReportEntry.objects.create(rawStderr="blah", **defaults),
    ]
    for c in reports:
        assert not c.triagedOnce
    user, _ = cmUser.objects.get_or_create(user=User.objects.get(username="test"))
    user.bucket_hit = True
    user.save()
    BucketWatch.objects.create(bucket=buckets[1], user=user)

    call_command("triage_new_reports")

    reports = [ReportEntry.objects.get(pk=c.pk) for c in reports]

    for c in reports:
        assert c.triagedOnce

    assert reports[0].bucket.pk == buckets[0].pk
    assert reports[1].bucket.pk == buckets[1].pk
    assert reports[2].bucket is None

    assert Notification.objects.count() == 1
    notification = Notification.objects.first()
    assert notification.level == "info"
    assert notification.recipient == user.user
    assert notification.unread
    assert notification.actor == buckets[1]
    assert notification.verb == "bucket_hit"
    assert (
        notification.description
        == f"The bucket {buckets[1].pk} received a new report entry {reports[1].pk}"
    )
    assert notification.target == reports[1]
