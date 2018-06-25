# coding: utf-8
'''Tests for CrashManager

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


LOG = logging.getLogger("fm.crashmanager.tests.crashmanager")
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


def test_crashmanager_redirect(client):
    """Request without login hits the login redirect"""
    resp = client.get('/')
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=/'


def test_crashmanager_no_login(client):
    """Request of root url redirects to crashes view"""
    client.login(username='test', password='test')
    resp = client.get('/')
    assert resp.status_code == requests.codes['found']
    assert resp.url == reverse('crashmanager:index')


def test_crashmanager_logout(client):
    """Logout url actually logs us out"""
    client.login(username='test', password='test')
    assert client.get(reverse('crashmanager:crashes')).status_code == requests.codes['ok']
    response = client.get(reverse('logout'))
    LOG.debug(response)
    response = client.get('/')
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == '/login/?next=/'


def test_crashmanager_noperm(client):
    """Request without permission results in 403"""
    client.login(username='test-noperm', password='test')
    resp = client.get(reverse('crashmanager:index'))
    assert resp.status_code == 403
