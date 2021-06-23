# coding: utf-8
'''Tests for CrashManager triage_new_crashes management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from notifications.models import Notification
import pytest
from crashmanager.models import Bucket, BucketWatch, Client, CrashEntry, OS, Platform, \
    Product, Tool, User as cmUser


pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("crashmanager_test")


def test_args():
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("triage_new_crashes", "")


def test_none():
    call_command("triage_new_crashes")


def test_some():
    buckets = [Bucket.objects.create(signature=json.dumps({"symptoms": [
               {'src': 'stderr',
                'type': 'output',
                'value': '/foo/'}]})),
               Bucket.objects.create(signature=json.dumps({"symptoms": [
                   {'src': 'stderr',
                    'type': 'output',
                    'value': '/match/'}]}))]
    defaults = {"client": Client.objects.create(),
                "os": OS.objects.create(),
                "platform": Platform.objects.create(),
                "product": Product.objects.create(),
                "tool": Tool.objects.create()}
    crashes = [CrashEntry.objects.create(bucket=buckets[0], rawStderr="match", **defaults),
               CrashEntry.objects.create(rawStderr="match", **defaults),
               CrashEntry.objects.create(rawStderr="blah", **defaults)]
    for c in crashes:
        assert not c.triagedOnce

    call_command("triage_new_crashes")

    crashes = [CrashEntry.objects.get(pk=c.pk) for c in crashes]

    for c in crashes:
        assert c.triagedOnce

    assert crashes[0].bucket.pk == buckets[0].pk
    assert crashes[1].bucket.pk == buckets[1].pk
    assert crashes[2].bucket is None


def test_some_with_notification():
    buckets = [Bucket.objects.create(signature=json.dumps({"symptoms": [
               {'src': 'stderr',
                'type': 'output',
                'value': '/foo/'}]})),
               Bucket.objects.create(signature=json.dumps({"symptoms": [
                   {'src': 'stderr',
                    'type': 'output',
                    'value': '/match/'}]}))]
    defaults = {"client": Client.objects.create(),
                "os": OS.objects.create(),
                "platform": Platform.objects.create(),
                "product": Product.objects.create(),
                "tool": Tool.objects.create()}
    crashes = [CrashEntry.objects.create(bucket=buckets[0], rawStderr="match", **defaults),
               CrashEntry.objects.create(rawStderr="match", **defaults),
               CrashEntry.objects.create(rawStderr="blah", **defaults)]
    for c in crashes:
        assert not c.triagedOnce
    user, _ = cmUser.objects.get_or_create(user=User.objects.get(username='test'))
    user.bucket_hit = True
    user.save()
    BucketWatch.objects.create(bucket=buckets[1], user=user)

    call_command("triage_new_crashes")

    crashes = [CrashEntry.objects.get(pk=c.pk) for c in crashes]

    for c in crashes:
        assert c.triagedOnce

    assert crashes[0].bucket.pk == buckets[0].pk
    assert crashes[1].bucket.pk == buckets[1].pk
    assert crashes[2].bucket is None

    assert Notification.objects.count() == 1
    notification = Notification.objects.first()
    assert notification.level == "info"
    assert notification.recipient == user.user
    assert notification.unread
    assert notification.actor == buckets[1]
    assert notification.verb == "bucket_hit"
    assert notification.description == f"The bucket {buckets[1].pk} received a new crash entry {crashes[1].pk}"
    assert notification.target == crashes[1]
