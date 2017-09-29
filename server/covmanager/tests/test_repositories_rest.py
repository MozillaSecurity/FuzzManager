'''
Tests for Repositories rest api.

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
#from ..models import 


#log = logging.getLogger("fm.covmanager.tests.repos.rest")


class RestRepositoriesTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/covmanager/rest/repositories/'
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/covmanager/rest/repositories/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/covmanager/rest/repositories/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/covmanager/rest/repositories/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/covmanager/rest/repositories/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should be allowed"""
        self.create_repository("git", name='testrepo')
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/covmanager/rest/repositories/')
        self.assertEqual(resp.status_code, httplib.OK)
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {"count", "previous", "results", "next"})
        self.assertEqual(resp['count'], 1)
        self.assertIsNone(resp['previous'])
        self.assertIsNone(resp['next'])
        self.assertEqual(len(resp['results']), 1)
        resp = resp['results'][0]
        self.assertEqual(set(resp.keys()), {'name'})
        self.assertEqual(resp['name'], 'testrepo')


class RestRepositoryTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/covmanager/rest/repositories/1/'
        self.assertEqual(self.client.get(url).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.post(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.put(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.patch(url, {}).status_code, httplib.UNAUTHORIZED)
        self.assertEqual(self.client.delete(url, {}).status_code, httplib.UNAUTHORIZED)

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/covmanager/rest/repositories/1/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/covmanager/rest/repositories/1/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/covmanager/rest/repositories/1/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/covmanager/rest/repositories/1/')
        self.assertEqual(resp.status_code, httplib.METHOD_NOT_ALLOWED)

    def test_get(self):
        """get should be allowed"""
        repo = self.create_repository("git", name='testrepo')
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/covmanager/rest/repositories/%d/' % repo.pk)
        self.assertEqual(resp.status_code, httplib.OK)
        resp = json.loads(resp.content)
        self.assertEqual(set(resp.keys()), {'name'})
        self.assertEqual(resp['name'], 'testrepo')
