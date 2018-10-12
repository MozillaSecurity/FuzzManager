'''
Tests for Collections rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import codecs
import json
import logging

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse  # noqa
from django.utils import dateparse, timezone
from rest_framework.test import APITestCase  # APIRequestFactory
import requests

from . import TestCase
from ..models import Collection


log = logging.getLogger("fm.covmanager.tests.collections.rest")  # pylint: disable=invalid-name


class RestCollectionsTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/covmanager/rest/collections/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/covmanager/rest/collections/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/covmanager/rest/collections/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        repo = self.create_repository("git", name="testrepo")
        cov = {"linesTotal": 0,
               "name": None,
               "coveragePercent": 0.0,
               "children": {},
               "linesMissed": 0,
               "linesCovered": 0}
        resp = self.client.post('/covmanager/rest/collections/', {"repository": "testrepo",
                                                                  "description": "testdesc",
                                                                  "coverage": json.dumps(cov),
                                                                  "branch": "master",
                                                                  "revision": "abc",
                                                                  "client": "testclient",
                                                                  "tools": "testtool"})
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['created'])
        self.assertEqual(Collection.objects.count(), 1)
        result = Collection.objects.all()[0]
        self.assertEqual(result.repository, repo)
        self.assertEqual(result.branch, 'master')
        self.assertLess((timezone.now() - result.created).total_seconds(), 60)
        self.assertEqual(result.description, 'testdesc')
        self.assertEqual(result.client.name, 'testclient')
        self.assertEqual(len(result.tools.all()), 1)
        self.assertEqual(result.tools.all()[0].name, 'testtool')
        self.assertEqual(result.revision, 'abc')
        self.assertEqual(json.load(codecs.getreader('utf-8')(result.coverage.file)), cov)

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/covmanager/rest/collections/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/covmanager/rest/collections/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should be allowed"""
        repo = self.create_repository('git', name='testrepo')
        coll = self.create_collection(repo, branch='master', description='testdesc', revision='abc')
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/covmanager/rest/collections/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'count', 'previous', 'results', 'next'})
        self.assertEqual(resp['count'], 1)
        self.assertIsNone(resp['previous'])
        self.assertIsNone(resp['next'])
        self.assertEqual(len(resp['results']), 1)
        resp = resp['results'][0]
        self.assertEqual(set(resp.keys()), {'branch', 'repository', 'created', 'description', 'client', 'coverage',
                                            'tools', 'id', 'revision'})
        self.assertEqual(resp['id'], coll.pk)
        self.assertEqual(resp['branch'], 'master')
        self.assertEqual(resp['repository'], 'testrepo')
        created = dateparse.parse_datetime(resp['created'])
        log.debug('time now: %s', timezone.now())
        self.assertLess((timezone.now() - created).total_seconds(), 60)
        self.assertEqual(resp['description'], 'testdesc')
        self.assertEqual(resp['client'], 'testclient')
        self.assertEqual(resp['tools'], 'testtool')
        self.assertEqual(resp['revision'], 'abc')
        self.assertEqual(resp['coverage'], coll.coverage.file)


class RestCollectionTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/covmanager/rest/collections/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/covmanager/rest/collections/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['forbidden'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/covmanager/rest/collections/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/covmanager/rest/collections/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/covmanager/rest/collections/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/covmanager/rest/collections/1/')
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get(self):
        """get should not be allowed"""
        repo = self.create_repository('git', name='testrepo')
        coll = self.create_collection(repo, branch='master', description='testdesc', revision='abc')
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/covmanager/rest/collections/%d/' % coll.pk)
        log.debug(resp)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'branch', 'repository', 'created', 'description', 'client', 'coverage',
                                            'tools', 'id', 'revision'})
        self.assertEqual(resp['id'], coll.pk)
        self.assertEqual(resp['branch'], 'master')
        self.assertEqual(resp['repository'], 'testrepo')
        created = dateparse.parse_datetime(resp['created'])
        log.debug('time now: %s', timezone.now())
        self.assertLess((timezone.now() - created).total_seconds(), 60)
        self.assertEqual(resp['description'], 'testdesc')
        self.assertEqual(resp['client'], 'testclient')
        self.assertEqual(resp['tools'], 'testtool')
        self.assertEqual(resp['revision'], 'abc')
        self.assertEqual(resp['coverage'], coll.coverage.file)
