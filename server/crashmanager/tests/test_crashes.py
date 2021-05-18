# coding: utf-8
'''Tests for Crashes view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
import pytest
import requests
from django.urls import reverse
from . import assert_contains


LOG = logging.getLogger("fm.crashmanager.tests.crashes")
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


def test_crashes_view(client):  # pylint: disable=invalid-name
    """Check that the Vue component is called"""
    client.login(username='test', password='test')
    response = client.get(reverse("crashmanager:crashes"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert response.context['restricted'] is False
    assert_contains(response, 'crasheslist')


@pytest.mark.parametrize(("name", "kwargs"),
                         [("crashmanager:crashes", {}),
                          ("crashmanager:crashdel", {'crashid': 0}),
                          ("crashmanager:crashedit", {'crashid': 0}),
                          ("crashmanager:crashview", {'crashid': 0})])
def test_crashes_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=' + path


@pytest.mark.parametrize("name",
                         ["crashmanager:crashdel",
                          "crashmanager:crashedit",
                          "crashmanager:crashview"])
def test_crash_simple_get(client, cm, name):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    crash = cm.create_crash()
    response = client.get(reverse(name, kwargs={"crashid": crash.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_delete_testcase(cm):
    """Testcases should be delete when TestCase object is removed"""
    testcase = cm.create_testcase("test.txt", "hello world")
    test_file = testcase.test.name
    storage = testcase.test.storage
    assert storage.exists(test_file)
    testcase.delete()
    if storage.exists(test_file):
        storage.delete(test_file)
        raise AssertionError("file should have been deleted with TestCase: %r" % (test_file,))


def test_delete_testcase_crash(cm):
    """Testcases should be delete when CrashInfo object is removed"""
    testcase = cm.create_testcase("test.txt", "hello world")
    test_file = testcase.test.name
    storage = testcase.test.storage
    assert storage.exists(test_file)
    crash = cm.create_crash(testcase=testcase)
    crash.delete()
    if storage.exists(test_file):
        storage.delete(test_file)
        raise AssertionError("file should have been deleted with CrashInfo: %r" % (test_file,))
