"""Tests for CrashManager cleanup_old_crashes management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from datetime import timedelta

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from crashmanager.models import (
    OS,
    Bucket,
    Bug,
    BugProvider,
    Client,
    CrashEntry,
    Platform,
    Product,
    Tool,
)

pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name


def _days_ago(n):
    return timezone.now() - timedelta(days=n)


def _crashentry_create(**kwds):
    if "client" not in kwds:
        kwds["client"] = Client.objects.get_or_create()[0]
    if "os" not in kwds:
        kwds["os"] = OS.objects.get_or_create()[0]
    if "platform" not in kwds:
        kwds["platform"] = Platform.objects.get_or_create()[0]
    if "product" not in kwds:
        kwds["product"] = Product.objects.get_or_create()[0]
    if "tool" not in kwds:
        kwds["tool"] = Tool.objects.get_or_create()[0]
    return CrashEntry.objects.create(**kwds)


def test_args():
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("cleanup_old_crashes", "")


def test_bug_cleanup():
    prov = BugProvider.objects.create()
    Bug.objects.create(externalType=prov)
    call_command("cleanup_old_crashes")
    assert Bug.objects.count() == 0


def test_closed_bugs(settings):
    """all buckets that have been closed for x days"""
    settings.CLEANUP_CRASHES_AFTER_DAYS = 4
    settings.CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 2

    prov = BugProvider.objects.create()
    bugs = (
        Bug.objects.create(externalType=prov),  # open
        Bug.objects.create(closed=_days_ago(1), externalType=prov),
        Bug.objects.create(closed=_days_ago(2), externalType=prov),
        Bug.objects.create(closed=_days_ago(3), externalType=prov),
    )
    buckets = [Bucket.objects.create(bug=b) for b in bugs]
    crashes = [_crashentry_create(bucket=b) for b in buckets]
    call_command("cleanup_old_crashes")
    assert set(Bug.objects.values_list("pk", flat=True)) == {o.pk for o in bugs[:-1]}
    assert set(Bucket.objects.values_list("pk", flat=True)) == {
        o.pk for o in buckets[:-1]
    }
    assert set(CrashEntry.objects.values_list("pk", flat=True)) == {
        o.pk for o in crashes[:-1]
    }


def test_empty_bucket(settings):
    """all buckets that are empty"""
    settings.CLEANUP_CRASHES_AFTER_DAYS = 4
    settings.CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 2

    prov = BugProvider.objects.create()
    bug = Bug.objects.create(externalType=prov)
    buckets = (
        Bucket.objects.create(),  # empty, no bug, no permanent
        Bucket.objects.create(bug=bug),
        Bucket.objects.create(permanent=True),  # empty, permanent
    )  # empty, has bug
    call_command("cleanup_old_crashes")
    # only the permanent bucket should remain
    assert set(Bucket.objects.values_list("pk", flat=True)) == {
        o.pk for o in buckets[2:]
    }


@pytest.mark.parametrize("bug", (True, False))
def test_inactive_bucket_cleanup(bug, settings):
    """test that buckets with only old crashes is cleaned up"""
    settings.CRASH_MAX_LIFETIME = 7

    bucket = Bucket.objects.create()
    if bug:
        prov = BugProvider.objects.create()
        bucket.bug = Bug.objects.create(externalType=prov)
        bucket.save()

    _crashentry_create(bucket=bucket, created=_days_ago(8))

    call_command("cleanup_old_crashes")

    assert CrashEntry.objects.count() == 0
    assert Bucket.objects.count() == 0
    assert Bug.objects.count() == 0


@pytest.mark.parametrize("bug", (True, False))
def test_inactive_bucket_cleanup_permanent(bug, settings):
    """test that permanent buckets with only old crashes is cleaned up"""
    settings.CRASH_MAX_LIFETIME = 7

    bucket = Bucket.objects.create(permanent=True)
    if bug:
        prov = BugProvider.objects.create()
        bucket.bug = Bug.objects.create(externalType=prov)
        bucket.save()

    _crashentry_create(bucket=bucket, created=_days_ago(8))

    call_command("cleanup_old_crashes")

    assert CrashEntry.objects.count() == 0
    assert Bucket.objects.count() == 1
    if bug:
        assert Bug.objects.count() == 1
    else:
        assert Bug.objects.count() == 0


def test_old_crashes(settings):
    """all entries that are older than x days and not in any bucket or bucket has no bug
    associated with it"""
    settings.CLEANUP_CRASHES_AFTER_DAYS = 3
    settings.CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 1

    prov = BugProvider.objects.create()
    buckets = (
        Bucket.objects.create(),  # bucket with no bug
        Bucket.objects.create(bug=Bug.objects.create(externalType=prov)),  # with bug
    )

    crashes = (
        _crashentry_create(),
        _crashentry_create(created=_days_ago(1)),
        _crashentry_create(created=_days_ago(2)),
        _crashentry_create(bucket=buckets[0]),
        _crashentry_create(bucket=buckets[0], created=_days_ago(1)),
        _crashentry_create(bucket=buckets[0], created=_days_ago(2)),
        _crashentry_create(bucket=buckets[1]),
        _crashentry_create(bucket=buckets[1], created=_days_ago(1)),
        _crashentry_create(bucket=buckets[1], created=_days_ago(2)),
        # bucket with a bug, not deleted
        _crashentry_create(bucket=buckets[1], created=_days_ago(3)),
        _crashentry_create(bucket=buckets[1], created=_days_ago(4)),
        _crashentry_create(bucket=buckets[1], created=_days_ago(5)),
        # edges of below cases that should not be deleted
        _crashentry_create(created=_days_ago(3)),
        _crashentry_create(bucket=buckets[0], created=_days_ago(3)),
        # no bucket, will be deleted
        _crashentry_create(created=_days_ago(4)),
        _crashentry_create(created=_days_ago(5)),
        _crashentry_create(created=_days_ago(6)),
        # bucket with no bug, will be deleted
        _crashentry_create(bucket=buckets[0], created=_days_ago(4)),
        _crashentry_create(bucket=buckets[0], created=_days_ago(5)),
        _crashentry_create(bucket=buckets[0], created=_days_ago(6)),
    )
    call_command("cleanup_old_crashes")
    assert set(CrashEntry.objects.values_list("pk", flat=True)) == {
        o.pk for o in crashes[:-6]
    }
    assert Bug.objects.count() == 1
    assert Bucket.objects.count() == 2
