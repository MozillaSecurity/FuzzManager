'''
Tests for Pools rest api.

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
from django.core.urlresolvers import reverse
from django.utils import timezone
from rest_framework.test import APITestCase  # APIRequestFactory

from . import TestCase
from ..models import InstancePool


log = logging.getLogger("fm.ec2spotmanager.tests.pools.rest")  # pylint: disable=invalid-name


class RestPoolCycleTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/pool/1/cycle/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/ec2spotmanager/rest/pool/1/cycle/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/pool/1/cycle/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should reset last_cycled"""
        config = self.create_config('testconfig')
        pool = self.create_pool(config, last_cycled=timezone.now())
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/cycle/' % pool.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['not_acceptable'])
        pool.isEnabled = True
        pool.save()
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/cycle/' % pool.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertTrue(pool.isEnabled)
        self.assertIsNone(pool.last_cycled)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/pool/1/cycle/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/pool/1/cycle/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/pool/1/cycle/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])


class RestPoolEnableTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/pool/1/enable/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/ec2spotmanager/rest/pool/1/enable/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/pool/1/enable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should flip isEnabled"""
        config = self.create_config('testconfig')
        pool = self.create_pool(config)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/enable/' % pool.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertTrue(pool.isEnabled)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/enable/' % pool.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['not_acceptable'])
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertTrue(pool.isEnabled)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/pool/1/enable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/pool/1/enable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/pool/1/enable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])


class RestPoolDisableTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/pool/1/disable/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/ec2spotmanager/rest/pool/1/disable/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/pool/1/disable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should flip isEnabled"""
        config = self.create_config('testconfig')
        pool = self.create_pool(config, enabled=True)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/disable/' % pool.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertFalse(pool.isEnabled)
        resp = self.client.post('/ec2spotmanager/rest/pool/%d/disable/' % pool.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['not_acceptable'])
        pool = InstancePool.objects.get(pk=pool.pk)
        self.assertFalse(pool.isEnabled)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/pool/1/disable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/pool/1/disable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/pool/1/disable/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])


@pytest.mark.xfail
class RestPoolChartDetailedTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1})
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1})
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should not be allowed"""
        pool = self.create_pool(self.create_config('testconfig', size=1))
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': pool.pk}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'poolid', 'labels', 'datasets', 'options', 'view'})


@pytest.mark.xfail
class RestPoolChartAccumulatedTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1})
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1})
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should be allowed"""
        pool = self.create_pool(self.create_config('testconfig'))
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': pool.pk}))
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'poolid', 'labels', 'datasets', 'options', 'view'})
