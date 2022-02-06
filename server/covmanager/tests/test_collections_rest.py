# coding: utf-8
'''Tests for Collections rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

from __future__ import annotations

import codecs
import json
import logging
import pytest
import requests
from django.contrib.auth.models import User
from django.utils import dateparse, timezone
from rest_framework.test import APIClient
from covmanager.models import Collection

from covmanager.tests.conftest import _result
from covmanager.tests.conftest import covType


LOG = logging.getLogger("fm.covmanager.tests.collections.rest")
pytestmark = pytest.mark.usefixtures("covmanager_test")  # pylint: disable=invalid-name


def test_rest_collections_no_auth(api_client: APIClient) -> None:
    """must yield forbidden without authentication"""
    url = '/covmanager/rest/collections/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_collections_no_perm(api_client: APIClient) -> None:
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/covmanager/rest/collections/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_collections_patch(api_client: APIClient) -> None:
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/covmanager/rest/collections/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collections_post(api_client: APIClient, cm: _result) -> None:
    """post should be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    repo = cm.create_repository("git", name="testrepo")

    cov: covType = {"linesTotal": 0,
           "name": None,
           "coveragePercent": 0.0,
           "children": {},
           "linesMissed": 0,
           "linesCovered": 0}
    resp = api_client.post('/covmanager/rest/collections/', {"repository": "testrepo",
                                                             "description": "testdesc",
                                                             "coverage": json.dumps(cov),
                                                             "branch": "master",
                                                             "revision": "abc",
                                                             "client": "testclient",
                                                             "tools": "testtool"})
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    assert Collection.objects.count() == 1
    result = Collection.objects.all()[0]
    assert result.repository == repo
    assert result.branch == 'master'
    assert (timezone.now() - result.created).total_seconds() < 60
    assert result.description == 'testdesc'
    assert result.client.name == 'testclient'
    assert len(result.tools.all()) == 1
    assert result.tools.all()[0].name == 'testtool'
    assert result.revision == 'abc'
    assert json.load(codecs.getreader('utf-8')(result.coverage.file)) == cov


def test_rest_collections_put(api_client: APIClient) -> None:
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/covmanager/rest/collections/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collections_delete(api_client: APIClient) -> None:
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/covmanager/rest/collections/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collections_get(api_client: APIClient, cm: _result) -> None:
    """get should be allowed"""
    repo = cm.create_repository('git', name='testrepo')
    coll = cm.create_collection(repo, branch='master', description='testdesc', revision='abc')
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/covmanager/rest/collections/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'count', 'previous', 'results', 'next'}
    assert resp['count'] == 1
    assert resp['previous'] is None
    assert resp['next'] is None
    assert len(resp['results']) == 1
    resp = resp['results'][0]
    assert set(resp.keys()) == {'branch', 'repository', 'created', 'description', 'client', 'coverage', 'tools',
                                'id', 'revision'}
    assert resp['id'] == coll.pk
    assert resp['branch'] == 'master'
    assert resp['repository'] == 'testrepo'
    created = dateparse.parse_datetime(resp['created'])
    LOG.debug('time now: %s', timezone.now())
    assert created is not None
    assert (timezone.now() - created).total_seconds() < 60
    assert resp['description'] == 'testdesc'
    assert resp['client'] == 'testclient'
    assert resp['tools'] == 'testtool'
    assert resp['revision'] == 'abc'
    assert resp['coverage'] == coll.coverage.file


def test_rest_collection_no_auth(api_client: APIClient) -> None:
    """must yield forbidden without authentication"""
    url = '/covmanager/rest/collections/1/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_collection_no_perm(api_client: APIClient) -> None:
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/covmanager/rest/collections/1/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_collection_patch(api_client: APIClient) -> None:
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/covmanager/rest/collections/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collection_post(api_client: APIClient) -> None:
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/covmanager/rest/collections/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collection_put(api_client: APIClient) -> None:
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/covmanager/rest/collections/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collection_delete(api_client: APIClient) -> None:
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/covmanager/rest/collections/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_collection_get(api_client: APIClient, cm: _result) -> None:
    """get should not be allowed"""
    repo = cm.create_repository('git', name='testrepo')
    coll = cm.create_collection(repo, branch='master', description='testdesc', revision='abc')
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/covmanager/rest/collections/%d/' % coll.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'branch', 'repository', 'created', 'description', 'client', 'coverage', 'tools',
                                'id', 'revision'}
    assert resp['id'] == coll.pk
    assert resp['branch'] == 'master'
    assert resp['repository'] == 'testrepo'
    created = dateparse.parse_datetime(resp['created'])
    LOG.debug('time now: %s', timezone.now())
    assert created is not None
    assert (timezone.now() - created).total_seconds() < 60
    assert resp['description'] == 'testdesc'
    assert resp['client'] == 'testclient'
    assert resp['tools'] == 'testtool'
    assert resp['revision'] == 'abc'
    assert resp['coverage'] == coll.coverage.file
