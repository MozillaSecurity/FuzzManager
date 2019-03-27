# coding: utf-8
'''
Tests for Machine status rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import requests
import pytest
from django.contrib.auth.models import User
from ec2spotmanager.models import Instance
from . import create_instance


LOG = logging.getLogger("fm.ec2spotmanager.tests.status.rest")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name


def test_rest_status_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/ec2spotmanager/rest/report/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']


def test_rest_status_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/ec2spotmanager/rest/report/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url, {}).status_code == requests.codes['forbidden']
    assert api_client.put(url, {}).status_code == requests.codes['forbidden']
    assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
    assert api_client.delete(url, {}).status_code == requests.codes['forbidden']


def test_rest_status_get(api_client):
    """get always returns an empty object"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/report/')
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert resp == {}


def test_rest_status_report(api_client):
    """post should update the status field on the instance"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    host = create_instance('host1')
    resp = api_client.post('/ec2spotmanager/rest/report/', {'client': 'host1', 'status_data': 'data'})
    assert resp.status_code == requests.codes['created']
    resp = json.loads(resp.content.decode('utf-8'))
    assert resp == {'status_data': 'data'}
    host = Instance.objects.get(pk=host.pk)  # re-read
    assert host.status_data == 'data'
    resp = api_client.post('/ec2spotmanager/rest/report/', {'client': 'host1'})
    assert resp.status_code == requests.codes['created']
    host = Instance.objects.get(pk=host.pk)  # re-read
    assert host.status_data is None
    resp = api_client.post('/ec2spotmanager/rest/report/')
    assert resp.status_code == requests.codes['bad_request']
    resp = api_client.post('/ec2spotmanager/rest/report/', {'client': 'host2'})
    assert resp.status_code == requests.codes['not_found']


def test_rest_status_report2(api_client):
    """post should update the status field on the instance"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    host1 = create_instance('host1')
    host2 = create_instance('host2')
    resp = api_client.post('/ec2spotmanager/rest/report/', {'client': 'host1', 'status_data': 'data'})
    assert resp.status_code == requests.codes['created']
    resp = json.loads(resp.content.decode('utf-8'))
    assert resp == {'status_data': 'data'}
    host1 = Instance.objects.get(pk=host1.pk)  # re-read
    assert host1.status_data == 'data'
    resp = api_client.post('/ec2spotmanager/rest/report/', {'client': 'host2', 'status_data': 'data2'})
    assert resp.status_code == requests.codes['created']
    resp = json.loads(resp.content.decode('utf-8'))
    assert resp == {'status_data': 'data2'}
    host2 = Instance.objects.get(pk=host2.pk)  # re-read
    assert host2.status_data == 'data2'
    host1 = Instance.objects.get(pk=host1.pk)  # re-read
    assert host1.status_data == 'data'


def test_rest_status_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/ec2spotmanager/rest/report/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_status_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/ec2spotmanager/rest/report/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_status_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/ec2spotmanager/rest/report/')
    assert resp.status_code == requests.codes['method_not_allowed']
