# coding: utf-8
'''Tests for TaskManager views

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
from . import create_pool

LOG = logging.getLogger("fm.taskmanager.tests.views")
pytestmark = pytest.mark.usefixtures("taskmanager_test")  # pylint: disable=invalid-name


@pytest.mark.parametrize("name", ["taskmanager:index",
                                  "taskmanager:pool-list-ui"])
def test_views_no_login(name, client):
    """Request without login hits the login redirect"""
    path = reverse(name)
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_index_simple_get(client):
    """Index redirects"""
    client.login(username='test', password='test')
    response = client.get(reverse("taskmanager:index"))
    LOG.debug(response)
    assert response.status_code == requests.codes["found"]
    assert response["Location"] == reverse("taskmanager:pool-list-ui")


def test_view_simple_get(client):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    response = client.get(reverse("taskmanager:pool-list-ui"))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_detail_view_no_login(client):
    pool = create_pool()
    path = reverse("taskmanager:pool-view-ui", args=(pool.pk,))
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_detail_view_simple_get(client):
    pool = create_pool()
    path = reverse("taskmanager:pool-view-ui", args=(pool.pk,))
    client.login(username='test', password='test')
    response = client.get(path)
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
