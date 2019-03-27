# coding: utf-8
'''Tests for Buckets rest api.

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


LOG = logging.getLogger("fm.crashmanager.tests.signatures.rest")
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


def test_rest_signatures_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/crashmanager/rest/buckets/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_signatures_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/crashmanager/rest/buckets/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_signatures_auth(api_client):
    """test that authenticated requests work"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['ok']


def test_rest_signatures_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signatures_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signatures_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signatures_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signatures_query_buckets(api_client, cm):
    """test that buckets can be queried"""
    bucket1 = cm.create_bucket(shortDescription="bucket #1")
    bucket2 = cm.create_bucket(shortDescription="bucket #2")
    buckets = [bucket1, bucket2, bucket1, bucket1]
    tests = [cm.create_testcase("test1.txt", quality=1),
             cm.create_testcase("test2.txt", quality=9),
             cm.create_testcase("test3.txt", quality=2),
             cm.create_testcase("test4.txt", quality=3)]
    for i in range(4):
        cm.create_crash(shortSignature="crash #%d" % (i + 1),
                        client="client #%d" % (i + 1),
                        os="os #%d" % (i + 1),
                        product="product #%d" % (i + 1),
                        product_version="%d" % (i + 1),
                        platform="platform #%d" % (i + 1),
                        tool="tool #1",
                        testcase=tests[i],
                        bucket=buckets[i])
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == 2
    assert resp['next'] is None
    assert resp['previous'] is None
    resp = resp['results']
    assert len(resp) == 2
    assert set(resp[0].keys()) == {'best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription',
                                   'signature', 'size'}
    if resp[0]['id'] == bucket1.pk:
        resp1 = resp[0]
        resp2 = resp[1]
        assert resp2['id'] == bucket2.pk
    else:
        resp1 = resp[1]
        resp2 = resp[0]
        assert resp1['id'] == bucket1.pk
        assert resp2['id'] == bucket2.pk
    assert resp1['best_quality'] == 1
    assert resp2['best_quality'] == 9
    assert resp1['bug'] is None
    assert resp2['bug'] is None
    assert not resp1['frequent']
    assert not resp2['frequent']
    assert not resp1['permanent']
    assert not resp2['permanent']
    assert resp1['shortDescription'] == "bucket #1"
    assert resp2['shortDescription'] == "bucket #2"
    assert resp1['signature'] == ""
    assert resp2['signature'] == ""
    assert resp1['size'] == 3
    assert resp2['size'] == 1


def test_rest_signature_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/crashmanager/rest/buckets/1/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_signature_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/crashmanager/rest/buckets/1/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_signature_auth(api_client):
    """test that authenticated requests work"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/buckets/')
    assert resp.status_code == requests.codes['ok']


def test_rest_signature_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/crashmanager/rest/buckets/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signature_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/crashmanager/rest/buckets/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signature_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/crashmanager/rest/buckets/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signature_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/buckets/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_signature_get(api_client, cm):
    """test that individual Signature can be fetched"""
    bucket = cm.create_bucket(shortDescription="bucket #1")
    tests = [cm.create_testcase("test1.txt", quality=9),
             cm.create_testcase("test3.txt", quality=2),
             cm.create_testcase("test4.txt", quality=3)]
    for i in range(3):
        cm.create_crash(shortSignature="crash #%d" % (i + 1),
                        client="client #%d" % (i + 1),
                        os="os #%d" % (i + 1),
                        product="product #%d" % (i + 1),
                        product_version="%d" % (i + 1),
                        platform="platform #%d" % (i + 1),
                        tool="tool #1",
                        testcase=tests[i],
                        bucket=bucket)
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/buckets/%d/' % bucket.pk)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription',
                                'signature', 'size'}
    assert resp['id'] == bucket.pk
    assert resp['best_quality'] == 2
    assert resp['bug'] is None
    assert not resp['frequent']
    assert not resp['permanent']
    assert resp['shortDescription'] == "bucket #1"
    assert resp['signature'] == ""
    assert resp['size'] == 3
