"""Tests for stats view.

Two parts:
- rest api for /rest/crashes/stats/
- celery task to update CrashHit table

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging
from datetime import timedelta

import pytest
import requests
from django.urls import reverse
from django.utils import timezone

from crashmanager.cron import update_crash_stats
from crashmanager.models import CrashHit, Tool

from . import assert_contains

LOG = logging.getLogger("fm.crashmanager.tests.stats")
VIEW_NAME = "crashmanager:stats"
API_NAME = "crashmanager:crash_stats_rest"
VIEW_ENTRIES_FMT = "Total reports in the last hour: %d"


def test_stats_view_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse(VIEW_NAME)
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


def test_stats_view_template(client, settings, user_normal):
    """Crash stats template has appropriate context"""
    client.login(username="test", password="test")
    settings.CLEANUP_CRASHES_AFTER_DAYS = 20
    response = client.get(reverse(VIEW_NAME))
    assert response.status_code == requests.codes["ok"]
    assert response.context["activity_range"] == 20
    assert response.context["providers"] == "[]"
    assert response.context["restricted"] is False
    assert_contains(response, "<crashstats")


def test_rest_stats_no_auth(api_client):
    """must yield forbidden without authentication"""
    assert (
        api_client.get(reverse(API_NAME)).status_code == requests.codes["unauthorized"]
    )
    assert (
        api_client.post(reverse(API_NAME)).status_code == requests.codes["unauthorized"]
    )
    assert (
        api_client.put(reverse(API_NAME)).status_code == requests.codes["unauthorized"]
    )
    assert (
        api_client.patch(reverse(API_NAME)).status_code
        == requests.codes["unauthorized"]
    )
    assert (
        api_client.delete(reverse(API_NAME)).status_code
        == requests.codes["unauthorized"]
    )


def test_rest_stats_no_perm(api_client, user_noperm):
    """must yield forbidden without permission"""
    assert api_client.get(reverse(API_NAME)).status_code == requests.codes["forbidden"]
    assert api_client.post(reverse(API_NAME)).status_code == requests.codes["forbidden"]
    assert api_client.put(reverse(API_NAME)).status_code == requests.codes["forbidden"]
    assert (
        api_client.patch(reverse(API_NAME)).status_code == requests.codes["forbidden"]
    )
    assert (
        api_client.delete(reverse(API_NAME)).status_code == requests.codes["forbidden"]
    )


def test_rest_stats_methods(api_client, user_normal):
    """post/put/patch/delete should not be allowed"""
    assert (
        api_client.post(reverse(API_NAME)).status_code
        == requests.codes["method_not_allowed"]
    )
    assert (
        api_client.put(reverse(API_NAME)).status_code
        == requests.codes["method_not_allowed"]
    )
    assert (
        api_client.patch(reverse(API_NAME)).status_code
        == requests.codes["method_not_allowed"]
    )
    assert (
        api_client.delete(reverse(API_NAME)).status_code
        == requests.codes["method_not_allowed"]
    )


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
def test_rest_stats_with_crashes(
    api_client, user, cm, ignore_toolfilter, settings
):  # pylint: disable=invalid-name
    """Insert crashes and check that they are shown ok."""
    settings.CRASH_STATS_MAX_HISTORY_DAYS = 9
    restricted = user.username != "test"
    bucket = cm.create_bucket(shortDescription="bucket #1")
    bucket2 = cm.create_bucket(shortDescription="bucket #2")
    cm.create_crash(shortSignature="crash #1", tool="tool #1")
    cm.create_crash(shortSignature="crash #2", tool="tool #1", bucket=bucket)
    cm.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket)
    cm.create_crash(shortSignature="crash #4", tool="tool #2")
    cm.create_crash(shortSignature="crash #5", tool="tool #2", bucket=bucket2)
    cm.create_crash(shortSignature="crash #6", tool="tool #2", bucket=bucket2)
    cm.create_crash(shortSignature="crash #7", tool="tool #2", bucket=bucket2)
    c8 = cm.create_crash(shortSignature="crash #8", tool="tool #2", bucket=bucket2)
    c8.created -= timedelta(days=1, seconds=1)
    c8.save()
    c9 = cm.create_crash(shortSignature="crash #9", tool="tool #2", bucket=bucket2)
    c9.created -= timedelta(hours=1, seconds=1)
    c9.save()
    cm.create_toolfilter("tool #1", user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    resp = api_client.get(reverse(API_NAME), params)

    assert resp.status_code == requests.codes["ok"], resp["detail"]
    resp = resp.json()
    assert resp.keys() == {
        "totals",
        "frequentBuckets",
        "outFilterGraphData",
        "inFilterGraphData",
    }
    assert set(resp["outFilterGraphData"]) == {0}
    assert set(resp["inFilterGraphData"]) == {0}
    assert len(resp["outFilterGraphData"]) == 9 * 24
    assert len(resp["inFilterGraphData"]) == 9 * 24
    del resp["outFilterGraphData"]
    del resp["inFilterGraphData"]

    if restricted or not ignore_toolfilter:
        assert resp == {
            "totals": [3, 3, 3],
            "frequentBuckets": {str(bucket.pk): [2, 2, 2]},
        }
    else:
        assert resp == {
            "totals": [7, 8, 9],
            "frequentBuckets": {
                str(bucket.pk): [2, 2, 2],
                str(bucket2.pk): [3, 4, 5],
            },
        }


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
def test_rest_stats_graph_data(api_client, user, cm, ignore_toolfilter, settings):
    """Check that crash stats graph data is returned"""
    settings.CRASH_STATS_MAX_HISTORY_DAYS = 9
    now = timezone.now()
    restricted = user.username != "test"
    t1 = Tool.objects.create(name="tool #1")
    t2 = Tool.objects.create(name="tool #2")
    for hr in range(settings.CRASH_STATS_MAX_HISTORY_DAYS * 24):
        CrashHit.objects.create(
            tool=t1, lastUpdate=now - timedelta(hours=hr), count=hr + 1
        )
        CrashHit.objects.create(
            tool=t2, lastUpdate=now - timedelta(hours=hr), count=hr + 1
        )
    cm.create_toolfilter("tool #1", user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    resp = api_client.get(reverse(API_NAME), params)
    assert resp.status_code == requests.codes["ok"], resp["detail"]
    resp = resp.json()
    assert len(resp["inFilterGraphData"]) == settings.CRASH_STATS_MAX_HISTORY_DAYS * 24
    assert len(resp["outFilterGraphData"]) == settings.CRASH_STATS_MAX_HISTORY_DAYS * 24
    assert resp["inFilterGraphData"] == list(
        range(settings.CRASH_STATS_MAX_HISTORY_DAYS * 24, 0, -1)
    )
    if restricted:
        assert resp["outFilterGraphData"] == [0] * (
            settings.CRASH_STATS_MAX_HISTORY_DAYS * 24
        )
    else:
        assert resp["outFilterGraphData"] == list(
            range(settings.CRASH_STATS_MAX_HISTORY_DAYS * 24, 0, -1)
        )


def test_update_crash_stats(db, cm, settings):
    """Check that crash stats are calculated by cron task"""
    settings.CRASH_STATS_MAX_HISTORY_DAYS = 9
    now = timezone.now()
    cm.create_crash(shortSignature="crash #1", tool="tool #1")
    cm.create_crash(shortSignature="crash #2", tool="tool #1")
    crs = cm.create_crash(shortSignature="crash #3", tool="tool #1")
    crs.created -= timedelta(hours=1)
    crs.save()
    crs = cm.create_crash(shortSignature="crash #4", tool="tool #1")
    crs.created -= timedelta(hours=6)
    crs.save()
    update_crash_stats()
    now = timezone.now()
    assert CrashHit.objects.count() == 3
    hit1, hit2, hit3 = CrashHit.objects.all().order_by("lastUpdate")
    assert abs(hit3.lastUpdate - now) < timedelta(seconds=10)
    orig_hit3_time = hit3.lastUpdate
    assert hit3.tool.name == "tool #1"
    assert hit3.count == 2
    assert abs(hit2.lastUpdate - now) - timedelta(hours=1) < timedelta(seconds=10)
    assert hit2.tool.name == "tool #1"
    assert hit2.count == 1
    assert abs(hit1.lastUpdate - now) - timedelta(hours=6) < timedelta(seconds=10)
    assert hit1.tool.name == "tool #1"
    assert hit1.count == 1
    cm.create_crash(shortSignature="crash #5", tool="tool #1")
    update_crash_stats()
    now = timezone.now()
    assert CrashHit.objects.count() == 3
    hit3 = CrashHit.objects.all().order_by("-lastUpdate")[0]
    assert abs(hit3.lastUpdate - now) < timedelta(seconds=10)
    assert hit3.tool.name == "tool #1"
    assert hit3.count == 3
    assert orig_hit3_time < hit3.lastUpdate
