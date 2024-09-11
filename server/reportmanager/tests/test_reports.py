"""Tests for Reports view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import logging

import pytest
import requests
from django.urls import reverse

from . import assert_contains

LOG = logging.getLogger("fm.reportmanager.tests.reports")
pytestmark = pytest.mark.usefixtures(
    "reportmanager_test"
)  # pylint: disable=invalid-name


def test_reports_view(client):  # pylint: disable=invalid-name
    """Check that the Vue component is called"""
    client.login(username="test", password="test")
    response = client.get(reverse("reportmanager:reports"))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
    assert response.context["restricted"] is False
    assert_contains(response, "reportslist")


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("reportmanager:reports", {}),
        ("reportmanager:reportdel", {"reportid": 0}),
        ("reportmanager:reportedit", {"reportid": 0}),
        ("reportmanager:reportview", {"reportid": 0}),
    ],
)
def test_reports_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


@pytest.mark.parametrize(
    "name",
    ["reportmanager:reportdel", "reportmanager:reportedit", "reportmanager:reportview"],
)
def test_report_simple_get(client, cm, name):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    report = cm.create_report()
    response = client.get(reverse(name, kwargs={"reportid": report.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_delete_testcase(cm):
    """Testcases should be delete when TestCase object is removed"""
    testcase = cm.create_testcase("test.txt", "hello world")
    test_file = testcase.test.name
    storage = testcase.test.storage
    assert storage.exists(test_file)
    testcase.delete()
    if storage.exists(test_file):
        storage.delete(test_file)
        raise AssertionError(
            f"file should have been deleted with TestCase: {test_file!r}"
        )


def test_delete_testcase_report(cm):
    """Testcases should be delete when ReportInfo object is removed"""
    testcase = cm.create_testcase("test.txt", "hello world")
    test_file = testcase.test.name
    storage = testcase.test.storage
    assert storage.exists(test_file)
    report = cm.create_report(testcase=testcase)
    report.delete()
    if storage.exists(test_file):
        storage.delete(test_file)
        raise AssertionError(
            f"file should have been deleted with ReportInfo: {test_file!r}"
        )
