"""Tests for ReportManager cleanup_old_reports management command

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

pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name


def _reportentry_create(**kwds):
    defaults = {
        "client": Client.objects.get_or_create()[0],
        "os": OS.objects.get_or_create()[0],
        "platform": Platform.objects.get_or_create()[0],
        "product": Product.objects.get_or_create()[0],
        "tool": Tool.objects.get_or_create()[0],
    }
    defaults.update(kwds)
    return ReportEntry.objects.create(**defaults)


def test_args():
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("cleanup_old_reports", "")


def test_bug_cleanup():
    prov = BugProvider.objects.create()
    Bug.objects.create(externalType=prov)
    call_command("cleanup_old_reports")
    assert Bug.objects.count() == 0


def test_closed_bugs(settings):
    """all buckets that have been closed for x days"""
    settings.CLEANUP_REPORTS_AFTER_DAYS = 4
    settings.CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 2

    prov = BugProvider.objects.create()
    bugs = (
        Bug.objects.create(externalType=prov),  # open
        Bug.objects.create(
            closed=timezone.now() - timedelta(days=1), externalType=prov
        ),  # closed 1 day ago
        Bug.objects.create(
            closed=timezone.now() - timedelta(days=2), externalType=prov
        ),  # closed 2 days ago
        Bug.objects.create(
            closed=timezone.now() - timedelta(days=3), externalType=prov
        ),
    )  # closed 3 days ago
    buckets = [Bucket.objects.create(bug=b) for b in bugs]
    reports = [_reportentry_create(bucket=b) for b in buckets]
    call_command("cleanup_old_reports")
    assert set(Bug.objects.values_list("pk", flat=True)) == {o.pk for o in bugs[:-1]}
    assert set(Bucket.objects.values_list("pk", flat=True)) == {
        o.pk for o in buckets[:-1]
    }
    assert set(ReportEntry.objects.values_list("pk", flat=True)) == {
        o.pk for o in reports[:-1]
    }


def test_empty_bucket(settings):
    """all buckets that are empty"""
    settings.CLEANUP_REPORTS_AFTER_DAYS = 4
    settings.CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 2

    prov = BugProvider.objects.create()
    bug = Bug.objects.create(externalType=prov)
    buckets = (
        Bucket.objects.create(),  # empty, no bug, no permanent
        Bucket.objects.create(permanent=True),  # empty, permanent
        Bucket.objects.create(bug=bug),
    )  # empty, has bug
    call_command("cleanup_old_reports")
    assert set(Bucket.objects.values_list("pk", flat=True)) == {
        o.pk for o in buckets[1:]
    }
    assert Bug.objects.count() == 1


def test_old_reports(settings):
    """all entries that are older than x days and not in any bucket or bucket has no bug
    associated with it"""
    settings.CLEANUP_REPORTS_AFTER_DAYS = 3
    settings.CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 1

    prov = BugProvider.objects.create()
    buckets = (
        Bucket.objects.create(),  # bucket with no bug
        Bucket.objects.create(bug=Bug.objects.create(externalType=prov)),
    )  # bucket with bug
    reports = (
        _reportentry_create(),
        _reportentry_create(created=timezone.now() - timedelta(days=1)),
        _reportentry_create(created=timezone.now() - timedelta(days=2)),
        _reportentry_create(bucket=buckets[0]),
        _reportentry_create(
            bucket=buckets[0], created=timezone.now() - timedelta(days=1)
        ),
        _reportentry_create(
            bucket=buckets[0], created=timezone.now() - timedelta(days=2)
        ),
        _reportentry_create(bucket=buckets[1]),
        _reportentry_create(
            bucket=buckets[1], created=timezone.now() - timedelta(days=1)
        ),
        _reportentry_create(
            bucket=buckets[1], created=timezone.now() - timedelta(days=2)
        ),
        # bucket with a bug, not deleted
        _reportentry_create(
            bucket=buckets[1], created=timezone.now() - timedelta(days=3)
        ),
        _reportentry_create(
            bucket=buckets[1], created=timezone.now() - timedelta(days=4)
        ),
        _reportentry_create(
            bucket=buckets[1], created=timezone.now() - timedelta(days=5)
        ),
        # edges of below cases that should not be deleted
        _reportentry_create(created=timezone.now() - timedelta(days=3)),
        _reportentry_create(
            bucket=buckets[0], created=timezone.now() - timedelta(days=3)
        ),
        # no bucket, will be deleted
        _reportentry_create(created=timezone.now() - timedelta(days=4)),
        _reportentry_create(created=timezone.now() - timedelta(days=5)),
        _reportentry_create(created=timezone.now() - timedelta(days=6)),
        # bucket with no bug, will be deleted
        _reportentry_create(
            bucket=buckets[0], created=timezone.now() - timedelta(days=4)
        ),
        _reportentry_create(
            bucket=buckets[0], created=timezone.now() - timedelta(days=5)
        ),
        _reportentry_create(
            bucket=buckets[0], created=timezone.now() - timedelta(days=6)
        ),
    )
    call_command("cleanup_old_reports")
    assert set(ReportEntry.objects.values_list("pk", flat=True)) == {
        o.pk for o in reports[:-6]
    }
    assert Bug.objects.count() == 1
    assert Bucket.objects.count() == 2
