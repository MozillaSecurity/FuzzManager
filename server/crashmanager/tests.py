'''
Tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

from models import CrashEntry

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase #APIRequestFactory

import httplib
import os.path
from urlparse import urlparse


class CrashManagerTests(TestCase):

    def setUp(self):
        User.objects.create_user('test', 'test@mozilla.com', 'test')

    def test_0(self):
        'test that request without login hits the login redirect'
        self.assertRedirects(self.client.get('/'), '/login/?next=/')

    def test_1(self):
        'test that request of root url redirects to crashes view'
        self.client.login(username='test', password='test')
        self.assertRedirects(self.client.get('/'), reverse('crashmanager:crashes'))


class RestCrashesTests(APITestCase):

    def setUp(self):
        User.objects.create_user('test', 'test@mozilla.com', 'test')

    def test_0(self):
        'must yield forbidden without authentication'
        url = '/crashmanager/rest/crashes/'
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_1(self):
        'test that authenticated requests work'
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/crashmanager/rest/crashes/')
        self.assertEqual(resp.status_code, httplib.OK)

    def test_2(self):
        'test that crash reporting works'
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
        self.assertEqual(resp.status_code, httplib.CREATED)
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

