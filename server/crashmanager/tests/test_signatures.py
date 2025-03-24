"""
Tests for signatures view.

@author:     Jesse Schwartzentruber (:truber)

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

from crashmanager.models import Bucket, BucketStatistics, BucketWatch, CrashEntry

from . import assert_contains

LOG = logging.getLogger("fm.crashmanager.tests.signatures")
pytestmark = pytest.mark.usefixtures(
    "crashmanager_test"
)  # pylint: disable=invalid-name


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("crashmanager:signatures", {}),
        ("crashmanager:findsigs", {"crashid": 0}),
        ("crashmanager:sigopt", {"sigid": 0}),
        ("crashmanager:sigtry", {"sigid": 0, "crashid": 0}),
        ("crashmanager:signew", {}),
        ("crashmanager:sigedit", {"sigid": 1}),
    ],
)
def test_signatures_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


def test_signatures_view(client):  # pylint: disable=invalid-name
    """Check that the Vue component is called"""
    client.login(username="test", password="test")
    response = client.get(reverse("crashmanager:signatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "signatureslist")


def test_del_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")

    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash1 = cm.create_crash(shortSignature="crash #1", tool="tool1")
    crash2 = cm.create_crash(shortSignature="crash #2", tool="tool2")
    crash3 = cm.create_crash(shortSignature="crash #3", tool="tool3")

    # no crashes
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(response, "Bucket contains no crash entries.")

    # 1 crash not in toolfilter
    cm.create_toolfilter(crash1.tool)
    crash2.bucket = bucket
    crash2.save()
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all crash entries with this bucket: 0 in tool filter, "
        "1 in other tools (tool2).",
    )

    # 1 crash in toolfilter
    crash1.bucket = bucket
    crash1.save()
    crash2.bucket = None
    crash2.save()
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all crash entries with this bucket: 1 in tool filter "
        "(none in other tools).",
    )

    # 1 crash in toolfilter, 1 not in toolfilter
    crash2.bucket = bucket
    crash2.save()
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all crash entries with this bucket: 1 in tool filter, "
        "1 in other tools (tool2).",
    )

    # 1 crash in toolfilter, 2 not in toolfilter
    crash3.bucket = bucket
    crash3.save()
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all crash entries with this bucket: 1 in tool filter, "
        "2 in other tools (tool2, tool3).",
    )


def test_find_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    crash = cm.create_crash()
    cm.create_bucket(
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "//"}]}
        )
    )

    response = client.get(
        reverse("crashmanager:findsigs", kwargs={"crashid": crash.pk})
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_opt_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "//"}]}
        )
    )
    response = client.get(reverse("crashmanager:sigopt", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_try_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "//"}]}
        )
    )
    crash = cm.create_crash()
    response = client.get(
        reverse("crashmanager:sigtry", kwargs={"sigid": bucket.pk, "crashid": crash.pk})
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_new_signature_view(client):
    """Check that the Vue component is called"""
    client.login(username="test", password="test")
    response = client.get(reverse("crashmanager:signew"))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "createoredit")


def test_edit_signature_view(client, cm):  # pylint: disable=invalid-name
    """Check that the Vue component is called"""
    client.login(username="test", password="test")
    sig = json.dumps(
        {"symptoms": [{"src": "stderr", "type": "output", "value": "/^blah/"}]}
    )
    bucket = cm.create_bucket(shortDescription="bucket #1", signature=sig)
    response = client.get(reverse("crashmanager:sigedit", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "createoredit")
    assert response.context["bucket"] == bucket


def test_del_signature_empty(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with no crashes"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    response = client.post(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("crashmanager:signatures")
    assert not Bucket.objects.count()


def test_del_signature_leave_entries(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with crashes and leave entries"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature="crash #1", bucket=bucket)
    response = client.post(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("crashmanager:signatures")
    assert not Bucket.objects.count()
    crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
    assert crash.bucket is None


def test_del_signature_del_entries(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with crashes and removing entries"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_crash(shortSignature="crash #1", bucket=bucket)
    response = client.post(
        reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}), {"delentries": "1"}
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("crashmanager:signatures")
    assert not Bucket.objects.count()
    assert not CrashEntry.objects.count()


def test_watch_signature_empty(client):
    """If no watched signatures, that should be shown"""
    client.login(username="test", password="test")
    response = client.get(reverse("crashmanager:sigwatch"))
    LOG.debug(response)
    assert_contains(
        response, "Displaying 0 watched signature entries from the database."
    )


def test_watch_signature_buckets(client, cm):  # pylint: disable=invalid-name
    """Watched signatures should be listed"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_bucketwatch(bucket=bucket)
    response = client.get(reverse("crashmanager:sigwatch"))
    LOG.debug(response)
    assert_contains(
        response, "Displaying 1 watched signature entries from the database."
    )
    siglist = response.context["siglist"]
    assert len(siglist) == 1
    assert siglist[0] == bucket


def test_watch_signature_buckets_new_crashes(
    client, cm
):  # pylint: disable=invalid-name
    """Watched signatures should show new crashes"""
    client.login(username="test", password="test")
    buckets = (
        cm.create_bucket(shortDescription="bucket #1"),
        cm.create_bucket(shortDescription="bucket #2"),
    )
    crash1 = cm.create_crash(
        shortSignature="crash #1", bucket=buckets[1], tool="tool #1"
    )
    cm.create_toolfilter("tool #1")
    cm.create_bucketwatch(bucket=buckets[0])
    cm.create_bucketwatch(bucket=buckets[1], crash=crash1)
    cm.create_crash(shortSignature="crash #2", bucket=buckets[1], tool="tool #1")
    response = client.get(reverse("crashmanager:sigwatch"))
    LOG.debug(response)
    assert_contains(
        response, "Displaying 2 watched signature entries from the database."
    )
    siglist = response.context["siglist"]
    assert len(siglist) == 2
    assert siglist[0] == buckets[1]
    assert siglist[0].newCrashes == 1
    assert siglist[1] == buckets[0]
    assert not siglist[1].newCrashes


def test_watch_signature_del(client, cm):  # pylint: disable=invalid-name
    """Deleting a signature watch"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_bucketwatch(bucket=bucket)
    response = client.get(
        reverse("crashmanager:sigwatchdel", kwargs={"sigid": bucket.pk})
    )
    LOG.debug(response)
    assert_contains(
        response,
        "Are you sure that you want to stop watching this signature for new crash "
        "entries?",
    )
    assert_contains(response, bucket.shortDescription)
    response = client.post(
        reverse("crashmanager:sigwatchdel", kwargs={"sigid": bucket.pk})
    )
    LOG.debug(response)
    assert not BucketWatch.objects.count()
    assert Bucket.objects.get() == bucket
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("crashmanager:sigwatch")


def test_watch_signature_delsig(client, cm):  # pylint: disable=invalid-name
    """Deleting a watched signature"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_bucketwatch(bucket=bucket)
    bucket.delete()
    assert not BucketWatch.objects.count()


def test_watch_signature_update(client, cm):  # pylint: disable=invalid-name
    """Updating a signature watch"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash1 = cm.create_crash(shortSignature="crash #1", bucket=bucket)
    watch = cm.create_bucketwatch(bucket=bucket, crash=crash1)
    crash2 = cm.create_crash(shortSignature="crash #2", bucket=bucket)
    response = client.post(
        reverse("crashmanager:sigwatchnew"),
        {"bucket": "%d" % bucket.pk, "crash": "%d" % crash2.pk},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("crashmanager:sigwatch")
    watch = BucketWatch.objects.get(pk=watch.pk)
    assert watch.bucket == bucket
    assert watch.lastCrash == crash2.pk


def test_watch_signature_new(client, cm):  # pylint: disable=invalid-name
    """Creating a signature watch"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature="crash #1", bucket=bucket)
    response = client.post(
        reverse("crashmanager:sigwatchnew"),
        {"bucket": "%d" % bucket.pk, "crash": "%d" % crash.pk},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("crashmanager:sigwatch")
    watch = BucketWatch.objects.get()
    assert watch.bucket == bucket
    assert watch.lastCrash == crash.pk


def test_watch_signature_crashes(client, cm):  # pylint: disable=invalid-name
    """Crashes in a signature watch should be shown correctly."""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    watch = cm.create_bucketwatch(bucket=bucket)
    response = client.get(
        reverse("crashmanager:sigwatchcrashes", kwargs={"sigid": bucket.pk})
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert response.context["watchId"] == watch.id
    assert response.context["restricted"] is False
    assert_contains(response, "crasheslist")


def test_bucket_statistics_creation(client, cm):
    """Test that BucketStatistics are created when crashes are added to buckets"""
    client.login(username="test", password="test")

    # Create bucket and crashes
    bucket = cm.create_bucket(shortDescription="bucket #1")

    cm.create_crash(shortSignature="crash #1", tool="tool1", bucket=bucket)
    cm.create_crash(shortSignature="crash #2", tool="tool1", bucket=bucket)
    cm.create_crash(shortSignature="crash #3", tool="tool2", bucket=bucket)

    # Verify statistics were created
    stats1 = BucketStatistics.objects.get(bucket=bucket, tool__name="tool1")
    assert stats1.size == 2

    stats2 = BucketStatistics.objects.get(bucket=bucket, tool__name="tool2")
    assert stats2.size == 1
