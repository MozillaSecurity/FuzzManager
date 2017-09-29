'''
Tests for Pools rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
import json
#import logging

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import timezone
import pytest
from rest_framework.test import APITestCase  # APIRequestFactory

from . import TestCase
from ..models import Instance, InstancePool


#log = logging.getLogger("fm.ec2spotmanager.tests.pools.rest")


class RestPoolCycleTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/pool/1/cycle/'
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/pool/1/cycle/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should reset last_cycled"""
        config = self.create_config('testconfig')
        pool = self.create_pool(config, last_cycled=timezone.now())
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/cycle/' % pool.pk)
        self.assertEqual(resp.status_code, httplib.NOT_ACCEPTABLE)
        pool.isEnabled = True
        pool.save()
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/cycle/' % pool.pk)
        self.assertEqual(resp.status_code, httplib.OK)
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertTrue(pool.isEnabled)
        self.assertIsNone(pool.last_cycled)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/pool/1/cycle/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/pool/1/cycle/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/pool/1/cycle/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)


class RestPoolEnableTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/pool/1/enable/'
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/pool/1/enable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should flip isEnabled"""
        config = self.create_config('testconfig')
        pool = self.create_pool(config)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/enable/' % pool.pk)
        self.assertEqual(resp.status_code, httplib.OK)
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertTrue(pool.isEnabled)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/enable/' % pool.pk)
        self.assertEqual(resp.status_code, httplib.NOT_ACCEPTABLE)
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertTrue(pool.isEnabled)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/pool/1/enable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/pool/1/enable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/pool/1/enable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)


class RestPoolDisableTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/pool/1/disable/'
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/pool/1/disable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should flip isEnabled"""
        config = self.create_config('testconfig')
        pool = self.create_pool(config, enabled=True)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/disable/' % pool.pk)
        self.assertEqual(resp.status_code, httplib.OK)
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertFalse(pool.isEnabled)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/disable/' % pool.pk)
        self.assertEqual(resp.status_code, httplib.NOT_ACCEPTABLE)
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertFalse(pool.isEnabled)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/pool/1/disable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/pool/1/disable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/pool/1/disable/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)


class RestPoolChartDetailedTests(APITestCase, TestCase):

    @pytest.mark.xfail  # these are protected by basic auth only
    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1})
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should not be allowed"""
        pool = self.create_pool(self.create_config('testconfig', size=1))
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': pool.pk}))
        self.assertEqual(resp.status_code, httplib.OK)
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {'poolid', 'labels', 'datasets', 'options', 'view'})

class RestPoolChartAccumulatedTests(APITestCase, TestCase):

    @pytest.mark.xfail  # these are protected by basic auth only
    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1})
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should be allowed"""
        pool = self.create_pool(self.create_config('testconfig'))
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': pool.pk}))
        self.assertEqual(resp.status_code, httplib.OK)
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {'poolid', 'labels', 'datasets', 'options', 'view'})
