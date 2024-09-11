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

from reportmanager.models import Bucket, BucketWatch, ReportEntry

from . import assert_contains

LOG = logging.getLogger("fm.reportmanager.tests.signatures")
pytestmark = pytest.mark.usefixtures(
    "reportmanager_test"
)  # pylint: disable=invalid-name


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("reportmanager:signatures", {}),
        ("reportmanager:findsigs", {"reportid": 0}),
        ("reportmanager:sigopt", {"sigid": 0}),
        ("reportmanager:sigtry", {"sigid": 0, "reportid": 0}),
        ("reportmanager:signew", {}),
        ("reportmanager:sigedit", {"sigid": 1}),
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
    response = client.get(reverse("reportmanager:signatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "signatureslist")


def test_del_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")

    bucket = cm.create_bucket(shortDescription="bucket #1")
    report1 = cm.create_report(shortSignature="report #1", tool="tool1")
    report2 = cm.create_report(shortSignature="report #2", tool="tool2")
    report3 = cm.create_report(shortSignature="report #3", tool="tool3")

    # no reports
    response = client.get(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(response, "Bucket contains no report entries.")

    # 1 report not in toolfilter
    cm.create_toolfilter(report1.tool)
    report2.bucket = bucket
    report2.save()
    response = client.get(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all report entries with this bucket: 0 in tool filter, "
        "1 in other tools (tool2).",
    )

    # 1 report in toolfilter
    report1.bucket = bucket
    report1.save()
    report2.bucket = None
    report2.save()
    response = client.get(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all report entries with this bucket: 1 in tool filter "
        "(none in other tools).",
    )

    # 1 report in toolfilter, 1 not in toolfilter
    report2.bucket = bucket
    report2.save()
    response = client.get(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all report entries with this bucket: 1 in tool filter, "
        "1 in other tools (tool2).",
    )

    # 1 report in toolfilter, 2 not in toolfilter
    report3.bucket = bucket
    report3.save()
    response = client.get(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(
        response,
        "Also delete all report entries with this bucket: 1 in tool filter, "
        "2 in other tools (tool2, tool3).",
    )


def test_find_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    report = cm.create_report()
    cm.create_bucket(
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "//"}]}
        )
    )

    response = client.get(
        reverse("reportmanager:findsigs", kwargs={"reportid": report.pk})
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
    response = client.get(reverse("reportmanager:sigopt", kwargs={"sigid": bucket.pk}))
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
    report = cm.create_report()
    response = client.get(
        reverse(
            "reportmanager:sigtry", kwargs={"sigid": bucket.pk, "reportid": report.pk}
        )
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_new_signature_view(client):
    """Check that the Vue component is called"""
    client.login(username="test", password="test")
    response = client.get(reverse("reportmanager:signew"))
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
    response = client.get(reverse("reportmanager:sigedit", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert_contains(response, "createoredit")
    assert response.context["bucket"] == bucket


def test_del_signature_empty(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with no reports"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    response = client.post(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("reportmanager:signatures")
    assert not Bucket.objects.count()


def test_del_signature_leave_entries(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with reports and leave entries"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    report = cm.create_report(shortSignature="report #1", bucket=bucket)
    response = client.post(reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("reportmanager:signatures")
    assert not Bucket.objects.count()
    report = ReportEntry.objects.get(pk=report.pk)  # re-read
    assert report.bucket is None


def test_del_signature_del_entries(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with reports and removing entries"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_report(shortSignature="report #1", bucket=bucket)
    response = client.post(
        reverse("reportmanager:sigdel", kwargs={"sigid": bucket.pk}),
        {"delentries": "1"},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("reportmanager:signatures")
    assert not Bucket.objects.count()
    assert not ReportEntry.objects.count()


def test_watch_signature_empty(client):
    """If no watched signatures, that should be shown"""
    client.login(username="test", password="test")
    response = client.get(reverse("reportmanager:sigwatch"))
    LOG.debug(response)
    assert_contains(
        response, "Displaying 0 watched signature entries from the database."
    )


def test_watch_signature_buckets(client, cm):  # pylint: disable=invalid-name
    """Watched signatures should be listed"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_bucketwatch(bucket=bucket)
    response = client.get(reverse("reportmanager:sigwatch"))
    LOG.debug(response)
    assert_contains(
        response, "Displaying 1 watched signature entries from the database."
    )
    siglist = response.context["siglist"]
    assert len(siglist) == 1
    assert siglist[0] == bucket


def test_watch_signature_buckets_new_reports(
    client, cm
):  # pylint: disable=invalid-name
    """Watched signatures should show new reports"""
    client.login(username="test", password="test")
    buckets = (
        cm.create_bucket(shortDescription="bucket #1"),
        cm.create_bucket(shortDescription="bucket #2"),
    )
    report1 = cm.create_report(
        shortSignature="report #1", bucket=buckets[1], tool="tool #1"
    )
    cm.create_toolfilter("tool #1")
    cm.create_bucketwatch(bucket=buckets[0])
    cm.create_bucketwatch(bucket=buckets[1], report=report1)
    cm.create_report(shortSignature="report #2", bucket=buckets[1], tool="tool #1")
    response = client.get(reverse("reportmanager:sigwatch"))
    LOG.debug(response)
    assert_contains(
        response, "Displaying 2 watched signature entries from the database."
    )
    siglist = response.context["siglist"]
    assert len(siglist) == 2
    assert siglist[0] == buckets[1]
    assert siglist[0].newReports == 1
    assert siglist[1] == buckets[0]
    assert not siglist[1].newReports


def test_watch_signature_del(client, cm):  # pylint: disable=invalid-name
    """Deleting a signature watch"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_bucketwatch(bucket=bucket)
    response = client.get(
        reverse("reportmanager:sigwatchdel", kwargs={"sigid": bucket.pk})
    )
    LOG.debug(response)
    assert_contains(
        response,
        "Are you sure that you want to stop watching this signature for new report "
        "entries?",
    )
    assert_contains(response, bucket.shortDescription)
    response = client.post(
        reverse("reportmanager:sigwatchdel", kwargs={"sigid": bucket.pk})
    )
    LOG.debug(response)
    assert not BucketWatch.objects.count()
    assert Bucket.objects.get() == bucket
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("reportmanager:sigwatch")


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
    report1 = cm.create_report(shortSignature="report #1", bucket=bucket)
    watch = cm.create_bucketwatch(bucket=bucket, report=report1)
    report2 = cm.create_report(shortSignature="report #2", bucket=bucket)
    response = client.post(
        reverse("reportmanager:sigwatchnew"),
        {"bucket": "%d" % bucket.pk, "report": "%d" % report2.pk},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("reportmanager:sigwatch")
    watch = BucketWatch.objects.get(pk=watch.pk)
    assert watch.bucket == bucket
    assert watch.lastReport == report2.pk


def test_watch_signature_new(client, cm):  # pylint: disable=invalid-name
    """Creating a signature watch"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    report = cm.create_report(shortSignature="report #1", bucket=bucket)
    response = client.post(
        reverse("reportmanager:sigwatchnew"),
        {"bucket": "%d" % bucket.pk, "report": "%d" % report.pk},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response.url == reverse("reportmanager:sigwatch")
    watch = BucketWatch.objects.get()
    assert watch.bucket == bucket
    assert watch.lastReport == report.pk


def test_watch_signature_reports(client, cm):  # pylint: disable=invalid-name
    """Reports in a signature watch should be shown correctly."""
    client.login(username="test", password="test")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    watch = cm.create_bucketwatch(bucket=bucket)
    response = client.get(
        reverse("reportmanager:sigwatchreports", kwargs={"sigid": bucket.pk})
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert response.context["watchId"] == watch.id
    assert response.context["restricted"] is False
    assert_contains(response, "reportslist")
