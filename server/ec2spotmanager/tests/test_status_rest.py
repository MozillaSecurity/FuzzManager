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
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from . import TestCase
from ..models import Instance


log = logging.getLogger("fm.ec2spotmanager.tests.status.rest")  # pylint: disable=invalid-name


class RestStatusTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/report/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/ec2spotmanager/rest/report/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url, {}).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url, {}).status_code, requests.codes['forbidden'])

    def test_get(self):
        """get always returns an empty object"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/report/')
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(resp, {})

    def test_report(self):
        """post should update the status field on the instance"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        host = self.create_instance('host1')
        resp = self.client.post('/ec2spotmanager/rest/report/', {'client': 'host1', 'status_data': 'data'})
        self.assertEqual(resp.status_code, requests.codes['created'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(resp, {'status_data': 'data'})
        host = Instance.objects.get(pk=host.pk)  # re-read
        self.assertEqual(host.status_data, 'data')
        resp = self.client.post('/ec2spotmanager/rest/report/', {'client': 'host1'})
        self.assertEqual(resp.status_code, requests.codes['created'])
        host = Instance.objects.get(pk=host.pk)  # re-read
        self.assertIsNone(host.status_data)
        resp = self.client.post('/ec2spotmanager/rest/report/')
        self.assertEqual(resp.status_code, requests.codes['bad_request'])
        resp = self.client.post('/ec2spotmanager/rest/report/', {'client': 'host2'})
        self.assertEqual(resp.status_code, requests.codes['not_found'])

    def test_report2(self):
        """post should update the status field on the instance"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        host1 = self.create_instance('host1')
        host2 = self.create_instance('host2')
        resp = self.client.post('/ec2spotmanager/rest/report/', {'client': 'host1', 'status_data': 'data'})
        self.assertEqual(resp.status_code, requests.codes['created'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(resp, {'status_data': 'data'})
        host1 = Instance.objects.get(pk=host1.pk)  # re-read
        self.assertEqual(host1.status_data, 'data')
        resp = self.client.post('/ec2spotmanager/rest/report/', {'client': 'host2', 'status_data': 'data2'})
        self.assertEqual(resp.status_code, requests.codes['created'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(resp, {'status_data': 'data2'})
        host2 = Instance.objects.get(pk=host2.pk)  # re-read
        self.assertEqual(host2.status_data, 'data2')
        host1 = Instance.objects.get(pk=host1.pk)  # re-read
        self.assertEqual(host1.status_data, 'data')

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/report/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/report/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/report/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])
