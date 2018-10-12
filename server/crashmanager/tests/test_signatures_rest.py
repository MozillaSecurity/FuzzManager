'''
Tests for Buckets rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import logging

import requests
from django.contrib.auth.models import User
from rest_framework.test import APITestCase  # APIRequestFactory

from . import TestCase


log = logging.getLogger("fm.crashmanager.tests.signatures.rest")  # pylint: disable=invalid-name


class RestSignaturesTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/crashmanager/rest/buckets/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/crashmanager/rest/buckets/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['forbidden'])

    def test_auth(self):
        """test that authenticated requests work"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['ok'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_query_buckets(self):
        """test that buckets can be queried"""
        bucket1 = self.create_bucket(shortDescription="bucket #1")
        bucket2 = self.create_bucket(shortDescription="bucket #2")
        buckets = [bucket1, bucket2, bucket1, bucket1]
        tests = [self.create_testcase("test1.txt", quality=1),
                 self.create_testcase("test2.txt", quality=9),
                 self.create_testcase("test3.txt", quality=2),
                 self.create_testcase("test4.txt", quality=3)]
        for i in range(4):
            self.create_crash(shortSignature="crash #%d" % (i + 1),
                              client="client #%d" % (i + 1),
                              os="os #%d" % (i + 1),
                              product="product #%d" % (i + 1),
                              product_version="%d" % (i + 1),
                              platform="platform #%d" % (i + 1),
                              tool="tool #1",
                              testcase=tests[i],
                              bucket=buckets[i])
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(resp['count'], 2)
        self.assertEqual(resp['next'], None)
        self.assertEqual(resp['previous'], None)
        resp = resp['results']
        self.assertEqual(len(resp), 2)
        self.assertEqual(set(resp[0].keys()), {'best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription',
                                               'signature', 'size'})
        if resp[0]['id'] == bucket1.pk:
            resp1 = resp[0]
            resp2 = resp[1]
            self.assertEqual(resp2['id'], bucket2.pk)
        else:
            resp1 = resp[1]
            resp2 = resp[0]
            self.assertEqual(resp1['id'], bucket1.pk)
            self.assertEqual(resp2['id'], bucket2.pk)
        self.assertEqual(resp1['best_quality'], 1)
        self.assertEqual(resp2['best_quality'], 9)
        self.assertEqual(resp1['bug'], None)
        self.assertEqual(resp2['bug'], None)
        self.assertEqual(resp1['frequent'], False)
        self.assertEqual(resp2['frequent'], False)
        self.assertEqual(resp1['permanent'], False)
        self.assertEqual(resp2['permanent'], False)
        self.assertEqual(resp1['shortDescription'], "bucket #1")
        self.assertEqual(resp2['shortDescription'], "bucket #2")
        self.assertEqual(resp1['signature'], "")
        self.assertEqual(resp2['signature'], "")
        self.assertEqual(resp1['size'], 3)
        self.assertEqual(resp2['size'], 1)


class RestSignatureTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/crashmanager/rest/buckets/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/crashmanager/rest/buckets/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['forbidden'])

    def test_auth(self):
        """test that authenticated requests work"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/buckets/')
        self.assertEqual(resp.status_code, requests.codes['ok'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/crashmanager/rest/buckets/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/crashmanager/rest/buckets/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/crashmanager/rest/buckets/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/crashmanager/rest/buckets/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """test that individual Signature can be fetched"""
        bucket = self.create_bucket(shortDescription="bucket #1")
        tests = [self.create_testcase("test1.txt", quality=9),
                 self.create_testcase("test3.txt", quality=2),
                 self.create_testcase("test4.txt", quality=3)]
        for i in range(3):
            self.create_crash(shortSignature="crash #%d" % (i + 1),
                              client="client #%d" % (i + 1),
                              os="os #%d" % (i + 1),
                              product="product #%d" % (i + 1),
                              product_version="%d" % (i + 1),
                              platform="platform #%d" % (i + 1),
                              tool="tool #1",
                              testcase=tests[i],
                              bucket=bucket)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/buckets/%d/' % bucket.pk)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription',
                                            'signature', 'size'})
        self.assertEqual(resp['id'], bucket.pk)
        self.assertEqual(resp['best_quality'], 2)
        self.assertEqual(resp['bug'], None)
        self.assertEqual(resp['frequent'], False)
        self.assertEqual(resp['permanent'], False)
        self.assertEqual(resp['shortDescription'], "bucket #1")
        self.assertEqual(resp['signature'], "")
        self.assertEqual(resp['size'], 3)
