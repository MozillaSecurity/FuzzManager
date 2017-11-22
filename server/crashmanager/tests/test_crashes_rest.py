'''
Tests for Crashes rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import logging
import os.path

import requests
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from . import TestCase
from ..models import CrashEntry, TestCase as cmTestCase


log = logging.getLogger("fm.crashmanager.tests.crashes.rest")  # pylint: disable=invalid-name


class RestCrashesTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/crashmanager/rest/crashes/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_auth(self):
        """test that authenticated requests work"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/crashes/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/crashmanager/rest/crashes/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/crashmanager/rest/crashes/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/crashmanager/rest/crashes/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_report_crash(self):
        """test that crash reporting works"""
        data = {
            'rawStdout': 'data on\nstdout',
            'rawStderr': 'data on\nstderr',
            'rawCrashData': 'some\ncrash\ndata',
            'testcase': 'foo();\ntest();',
            'testcase_isbinary': False,
            'testcase_quality': 0,
            'testcase_ext': 'js',
            'platform': 'x86',
            'product': 'mozilla-central',
            'product_version': 'badf00d',
            'os': 'linux',
            'client': 'client1',
            'tool': 'tool1'}
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/crashmanager/rest/crashes/', data=data)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['created'])
        crash = CrashEntry.objects.get()
        for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
            self.assertEqual(getattr(crash, field), data[field])
        self.assertEqual(os.path.splitext(crash.testcase.test.path)[1].lstrip('.'), data['testcase_ext'])
        with open(crash.testcase.test.path) as fp:
            self.assertEqual(fp.read(), data['testcase'])
        self.assertEqual(crash.testcase.isBinary, data['testcase_isbinary'])
        self.assertEqual(crash.testcase.quality, data['testcase_quality'])
        for field in ('platform', 'product', 'os', 'client', 'tool'):
            self.assertEqual(getattr(crash, field).name, data[field])
        self.assertEqual(crash.product.version, data['product_version'])

    def test_report_crash_no_test(self):
        """test that crash reporting works with no testcase"""
        data = {
            'rawStdout': 'data on\nstdout',
            'rawStderr': 'data on\nstderr',
            'rawCrashData': 'some\ncrash\ndata',
            'platform': 'x86',
            'product': 'mozilla-central',
            'product_version': 'badf00d',
            'os': 'linux',
            'client': 'client1',
            'tool': 'tool1'}
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/crashmanager/rest/crashes/', data=data)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['created'])
        crash = CrashEntry.objects.get()
        for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
            self.assertEqual(getattr(crash, field), data[field])
        self.assertIsNone(crash.testcase)
        for field in ('platform', 'product', 'os', 'client', 'tool'):
            self.assertEqual(getattr(crash, field).name, data[field])
        self.assertEqual(crash.product.version, data['product_version'])

    def test_report_crash_empty(self):
        """test that crash reporting works with empty fields where allowed"""
        data = {
            'rawStdout': '',
            'rawStderr': '',
            'rawCrashData': '',
            'testcase': 'blah',
            'testcase_isbinary': False,
            'testcase_quality': 0,
            'testcase_ext': '',
            'platform': 'x',
            'product': 'x',
            'product_version': '',
            'os': 'x',
            'client': 'x',
            'tool': 'x'}
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/crashmanager/rest/crashes/', data=data)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['created'])
        crash = CrashEntry.objects.get()
        for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
            self.assertEqual(getattr(crash, field), data[field])
        self.assertEqual(os.path.splitext(crash.testcase.test.path)[1].lstrip('.'), data['testcase_ext'])
        with open(crash.testcase.test.path) as fp:
            self.assertEqual(fp.read(), data['testcase'])
        self.assertEqual(crash.testcase.isBinary, data['testcase_isbinary'])
        self.assertEqual(crash.testcase.quality, data['testcase_quality'])
        for field in ('platform', 'product', 'os', 'client', 'tool'):
            self.assertEqual(getattr(crash, field).name, data[field])
        self.assertEqual(crash.product.version, data['product_version'])

    def test_query_crash(self):
        """test that crashes can be queried"""
        buckets = [self.create_bucket(shortDescription="bucket #1"), None, None, None]
        testcases = [self.create_testcase("test1.txt", quality=5),
                     self.create_testcase("test2.txt", quality=0),
                     self.create_testcase("test3.txt", quality=5),
                     self.create_testcase("test4.txt", quality=5)]
        tools = ["tool1", "tool1", "tool2", "tool1"]
        crashes = [self.create_crash(shortSignature="crash #%d" % (i + 1),
                                     client="client #%d" % (i + 1),
                                     os="os #%d" % (i + 1),
                                     product="product #%d" % (i + 1),
                                     product_version="%d" % (i + 1),
                                     platform="platform #%d" % (i + 1),
                                     tool=tools[i],
                                     bucket=buckets[i],
                                     testcase=testcases[i])
                   for i in range(4)]
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/crashes/',
                               {"query": json.dumps({"op": "AND",
                                                     "bucket": None,
                                                     "testcase__quality": 5,
                                                     "tool__name__in": ["tool1"]})})
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['next'], None)
        self.assertEqual(resp['previous'], None)
        self.assertEqual(len(resp['results']), 1)
        resp = resp['results'][0]
        self.assertEqual(set(resp.keys()), {'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
                                            'product', 'product_version', 'rawCrashData', 'rawStderr', 'rawStdout',
                                            'testcase', 'testcase_isbinary', 'testcase_quality', 'tool',
                                            'shortSignature', 'crashAddress'})
        for key, value in resp.items():
            if key == "testcase":
                continue
            attrs = {"client": "client_name",
                     "os": "os_name",
                     "platform": "platform_name",
                     "product": "product_name",
                     "testcase_isbinary": "testcase_isBinary",
                     "tool": "tool_name"}.get(key, key)
            result = crashes[3]
            for attr in attrs.split("_"):
                result = getattr(result, attr)
            self.assertEqual(value, result)

    def test_list_noraw(self):
        """test that crashes can be listed without raw fields"""
        testcase = self.create_testcase("test1.txt", quality=5)
        crash = self.create_crash(shortSignature="crash #1",
                                  client="client #1",
                                  os="os #1",
                                  product="product #1",
                                  product_version="1",
                                  platform="platform #1",
                                  tool="tool1",
                                  bucket=None,
                                  testcase=testcase)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/crashes/', {'include_raw': '0'})
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['next'], None)
        self.assertEqual(resp['previous'], None)
        self.assertEqual(len(resp['results']), 1)
        resp = resp['results'][0]
        self.assertEqual(set(resp.keys()), {'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
                                            'product', 'product_version', 'testcase', 'testcase_isbinary',
                                            'testcase_quality', 'tool', 'shortSignature', 'crashAddress'})
        for key, value in resp.items():
            if key == "testcase":
                continue
            attrs = {"client": "client_name",
                     "os": "os_name",
                     "platform": "platform_name",
                     "product": "product_name",
                     "testcase_isbinary": "testcase_isBinary",
                     "tool": "tool_name"}.get(key, key)
            result = crash
            for attr in attrs.split("_"):
                result = getattr(result, attr)
            self.assertEqual(value, result)


class RestCrashTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/crashmanager/rest/crashes/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_auth(self):
        """test that authenticated requests work"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/crashes/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/crashmanager/rest/crashes/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/crashmanager/rest/crashes/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/crashmanager/rest/crashes/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """test that individual CrashEntry can be fetched"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        test = self.create_testcase("test.txt", quality=0)
        bucket = self.create_bucket(shortDescription="bucket #1")
        crash = self.create_crash(shortSignature="crash #1",
                                  bucket=bucket,
                                  client="client #1",
                                  os="os #1",
                                  product="product #1",
                                  product_version="1",
                                  platform="platform #1",
                                  tool="tool #1",
                                  testcase=test)
        resp = self.client.get('/crashmanager/rest/crashes/%d/' % crash.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
                                            'product', 'product_version', 'rawCrashData', 'rawStderr', 'rawStdout',
                                            'testcase', 'testcase_isbinary', 'testcase_quality', 'tool',
                                            'shortSignature', 'crashAddress'})
        for key, value in resp.items():
            if key == "testcase":
                continue
            attrs = {"client": "client_name",
                     "os": "os_name",
                     "bucket": "bucket_pk",
                     "platform": "platform_name",
                     "product": "product_name",
                     "testcase_isbinary": "testcase_isBinary",
                     "tool": "tool_name"}.get(key, key)
            result = crash
            for attr in attrs.split("_"):
                result = getattr(result, attr)
            self.assertEqual(value, result)

    def test_update(self):
        """test that only allowed fields of CrashEntry can be updated"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        test = self.create_testcase("test.txt", quality=0)
        bucket = self.create_bucket(shortDescription="bucket #1")
        crash = self.create_crash(shortSignature="crash #1",
                                  bucket=bucket,
                                  client="client #1",
                                  os="os #1",
                                  product="product #1",
                                  product_version="1",
                                  platform="platform #1",
                                  tool="tool #1",
                                  testcase=test)
        fields = {'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform', 'product', 'product_version',
                  'rawCrashData', 'rawStderr', 'rawStdout', 'testcase', 'testcase_isbinary', 'tool',
                  'shortSignature', 'crashAddress'}
        for field in fields:
            resp = self.client.patch('/crashmanager/rest/crashes/%d/' % crash.pk, {field: ""})
            log.debug(resp)
            self.assertEqual(resp.status_code, requests.codes['bad_request'])
        resp = self.client.patch('/crashmanager/rest/crashes/%d/' % crash.pk, {"testcase_quality": "5"})
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        test = cmTestCase.objects.get(pk=test.pk)  # re-read
        self.assertEqual(test.quality, 5)
