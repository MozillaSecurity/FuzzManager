# coding: utf-8
'''Tests for stats view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import datetime
import logging
import pytest
import requests
from django.urls import reverse
from . import assert_contains


LOG = logging.getLogger("fm.crashmanager.tests.stats")
VIEW_NAME = "crashmanager:stats"
VIEW_ENTRIES_FMT = "Total reports in the last hour: %d"
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


def test_stats_view_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse(VIEW_NAME)
    resp = client.get(path)
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=' + path


def test_stats_view_no_crashes(client):
    """If no crashes in db, an appropriate message is shown."""
    client.login(username='test', password='test')
    response = client.get(reverse(VIEW_NAME))
    assert response.status_code == requests.codes['ok']
    assert response.context['total_reports_per_hour'] == 0
    assert_contains(response, VIEW_ENTRIES_FMT % 0)
    assert not response.context['frequentBuckets']


def test_stats_view_with_crash(client, cm):  # pylint: disable=invalid-name
    """Insert one crash and check that it is shown ok."""
    client.login(username='test', password='test')
    cm.create_crash(shortSignature="crash #1")
    response = client.get(reverse(VIEW_NAME))
    assert response.status_code == requests.codes['ok']
    assert response.context['total_reports_per_hour'] == 1
    assert_contains(response, VIEW_ENTRIES_FMT % 1)
    assert not response.context['frequentBuckets']


def test_stats_view_with_crashes(client, cm):  # pylint: disable=invalid-name
    """Insert crashes and check that they are shown ok."""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_crash(shortSignature="crash #1", tool="tool #1")
    cm.create_crash(shortSignature="crash #2", tool="tool #1", bucket=bucket)
    cm.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket)
    cm.create_crash(shortSignature="crash #4", tool="tool #2")
    cm.create_toolfilter("tool #1")
    response = client.get(reverse(VIEW_NAME))
    assert response.status_code == requests.codes['ok']
    assert response.context['total_reports_per_hour'] == 4
    assert_contains(response, VIEW_ENTRIES_FMT % 4)
    response_buckets = response.context['frequentBuckets']
    assert len(response_buckets) == 1
    assert response_buckets[0] == bucket
    assert response_buckets[0].rph == 2


def test_stats_view_old(client, cm):  # pylint: disable=invalid-name
    """Insert one crash in the past and check that it is not shown."""
    client.login(username='test', password='test')
    crash = cm.create_crash(shortSignature="crash #1")
    response = client.get(reverse(VIEW_NAME))
    assert response.status_code == requests.codes['ok']
    assert response.context['total_reports_per_hour'] == 1
    assert_contains(response, VIEW_ENTRIES_FMT % 1)
    assert not response.context['frequentBuckets']
    crash.created -= datetime.timedelta(hours=1, seconds=1)
    crash.save()
    response = client.get(reverse(VIEW_NAME))
    assert response.status_code == requests.codes['ok']
    assert response.context['total_reports_per_hour'] == 0
    assert_contains(response, VIEW_ENTRIES_FMT % 0)
    assert not response.context['frequentBuckets']
