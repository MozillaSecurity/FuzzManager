# coding: utf-8
'''Tests for Repositories rest api.

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
from django.contrib.auth.models import User


LOG = logging.getLogger("fm.covmanager.tests.repos.rest")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("covmanager_test")  # pylint: disable=invalid-name


def test_rest_repositories_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/covmanager/rest/repositories/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_repositories_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/covmanager/rest/repositories/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_repositories_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/covmanager/rest/repositories/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repositories_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/covmanager/rest/repositories/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repositories_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/covmanager/rest/repositories/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repositories_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/covmanager/rest/repositories/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repositories_get(api_client, cm):
    """get should be allowed"""
    cm.create_repository("git", name='testrepo')
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/covmanager/rest/repositories/')
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {"count", "previous", "results", "next"}
    assert resp['count'] == 1
    assert resp['previous'] is None
    assert resp['next'] is None
    assert len(resp['results']) == 1
    resp = resp['results'][0]
    assert set(resp.keys()) == {'name'}
    assert resp['name'] == 'testrepo'


def test_rest_repository_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/covmanager/rest/repositories/1/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_repository_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/covmanager/rest/repositories/1/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_repository_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/covmanager/rest/repositories/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repository_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/covmanager/rest/repositories/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repository_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/covmanager/rest/repositories/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repository_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/covmanager/rest/repositories/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_repository_get(api_client, cm):
    """get should be allowed"""
    repo = cm.create_repository("git", name='testrepo')
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/covmanager/rest/repositories/%d/' % repo.pk)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'name'}
    assert resp['name'] == 'testrepo'
