# coding: utf-8
'''Tests for CovManager collection views

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import os
import re
import pytest
import requests
from django.urls import reverse


LOG = logging.getLogger("fm.covmanager.tests.collections")
pytestmark = pytest.mark.usefixtures("covmanager_test")  # pylint: disable=invalid-name


@pytest.mark.parametrize("name", ["covmanager:collections",
                                  "covmanager:collections_api",
                                  "covmanager:collections_diff",
                                  "covmanager:collections_patch"])
def test_collections_no_login(name, client):
    """Request without login hits the login redirect"""
    path = reverse(name)
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


@pytest.mark.parametrize("name", ["covmanager:collections",
                                  "covmanager:collections_api",
                                  "covmanager:collections_diff",
                                  "covmanager:collections_patch"])
def test_collections_view_simple_get(name, client):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    response = client.get(reverse(name))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_collections_diff_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse("covmanager:collections_diff_api", kwargs={'path': ''})
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_collections_diff_simple_get(client, cm):
    """No errors are thrown in template"""
    repo = cm.create_repository("git")
    col1 = cm.create_collection(repository=repo, coverage=json.dumps({"children": []}))
    col2 = cm.create_collection(repository=repo, coverage=json.dumps({"children": []}))
    client.login(username='test', password='test')
    response = client.get(reverse("covmanager:collections_diff_api", kwargs={'path': ''}),
                          {'ids': '%d,%d' % (col1.pk, col2.pk)})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_collections_patch_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse("covmanager:collections_patch_api", kwargs={'collectionid': 0, 'patch_revision': 'abc'})
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_collections_patch_simple_get(client, cm):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    repo = cm.create_repository("hg")
    col = cm.create_collection(repository=repo,
                               coverage=json.dumps({"linesTotal": 1,
                                                    "name": None,
                                                    "coveragePercent": 0.0,
                                                    "children": {"test.c": {"coverage": []}},
                                                    "linesMissed": 1,
                                                    "linesCovered": 0}))
    with open(os.path.join(repo.location, "test.c"), "w") as fp:
        fp.write("hello")
    cm.hg(repo, "add", "test.c")
    cm.hg(repo, "commit", "-m", "init")
    with open(os.path.join(repo.location, "test.c"), "w") as fp:
        fp.write("world")
    cm.hg(repo, "commit", "-m", "update")
    rev = re.match(r"changeset:   1:([0-9a-f]+)", cm.hg(repo, "log")).group(1)
    response = client.get(reverse("covmanager:collections_patch_api",
                                  kwargs={'collectionid': col.pk, 'patch_revision': rev}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_collections_browse_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse("covmanager:collections_browse", kwargs={'collectionid': 0})
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_collections_browse_simple_get(client):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    response = client.get(reverse("covmanager:collections_browse", kwargs={'collectionid': 0}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_collections_browse_api_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse("covmanager:collections_browse_api", kwargs={'collectionid': 0, 'path': ''})
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_collections_browse_api_simple_get(client, cm):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    repo = cm.create_repository("git")
    col = cm.create_collection(repository=repo)
    response = client.get(reverse("covmanager:collections_browse_api", kwargs={'collectionid': col.pk, 'path': ''}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
