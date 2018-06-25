# coding: utf-8
'''Tests for CovManager repository views

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import pytest
import requests
from django.urls import reverse


LOG = logging.getLogger("fm.covmanager.tests.repos")
pytestmark = pytest.mark.usefixtures("covmanager_test")  # pylint: disable=invalid-name


@pytest.mark.parametrize("name", ["covmanager:repositories",
                                  "covmanager:repositories_search_api"])
def test_repositories_no_login(name, client):
    """Request without login hits the login redirect"""
    path = reverse(name)
    response = client.get(path, follow=False)
    assert response.status_code == requests.codes["found"]
    assert response.url == "/login/?next=" + path


def test_repositories_view_simpleget(client):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    response = client.get(reverse("covmanager:repositories"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_repositories_view_list(client, cm):
    """Repositories are listed"""
    client.login(username='test', password='test')
    repos = []
    if cm.have_git:
        repos.append(cm.create_repository("git", name="gittest1"))
        repos.append(cm.create_repository("git", name="gittest2"))
    if cm.have_hg:
        repos.append(cm.create_repository("hg", name="hgtest1"))
        repos.append(cm.create_repository("hg", name="hgtest2"))
    if not repos:
        pytest.skip("no repositories available")
    response = client.get(reverse("covmanager:repositories"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert set(response.context['repositories']) == set(repos)


def test_repositories_search_view_simpleget(client):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    response = client.get(reverse("covmanager:repositories_search_api"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_repositories_search_view_search_git(client, cm):
    cm.create_repository("git", name="gittest1")
    cm.create_repository("git", name="gittest2")
    client.login(username='test', password='test')
    response = client.get(reverse("covmanager:repositories_search_api"), {"name": "blah"})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    response = json.loads(response.content.decode('utf-8'))
    assert set(response.keys()) == {"results"}
    assert response["results"] == []
    response = client.get(reverse("covmanager:repositories_search_api"), {"name": "test"})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    response = json.loads(response.content.decode('utf-8'))
    assert set(response.keys()) == {"results"}
    assert set(response["results"]) == {"gittest1", "gittest2"}


def test_repositories_search_view_search_hg(client, cm):
    cm.create_repository("hg", name="hgtest1")
    cm.create_repository("hg", name="hgtest2")
    client.login(username='test', password='test')
    response = client.get(reverse("covmanager:repositories_search_api"), {"name": "blah"})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    response = json.loads(response.content.decode('utf-8'))
    assert set(response.keys()) == {"results"}
    assert response["results"] == []
    response = client.get(reverse("covmanager:repositories_search_api"), {"name": "test"})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    response = json.loads(response.content.decode('utf-8'))
    assert set(response.keys()) == {"results"}
    assert set(response["results"]) == {"hgtest1", "hgtest2"}
