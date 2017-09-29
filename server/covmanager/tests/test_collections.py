'''
Tests for CovManager collection views

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
import json
import logging
import os
import re

from django.core.urlresolvers import reverse
import pytest

from . import TestCase


log = logging.getLogger("fm.covmanager.tests.collections")


class CollectionsViewTests(TestCase):
    name = "covmanager:collections"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsApiViewTests(TestCase):
    name = "covmanager:collections_api"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.UNAUTHORIZED)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsDiffViewTests(TestCase):
    name = "covmanager:collections_diff"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsDiffApiViewTests(TestCase):
    name = "covmanager:collections_diff_api"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'path': ''})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        repo = self.create_repository("git")
        cov_path = self.mkstemp(prefix='testcov', dir=os.path.dirname(__file__))
        with open(cov_path, "w") as covf:
            json.dump({"children": []}, covf)
        cov1 = open(cov_path)
        self.addCleanup(cov1.close)
        cov2 = open(cov_path)
        self.addCleanup(cov2.close)
        col1 = self.create_collection(repository=repo, coverage=cov1)
        col2 = self.create_collection(repository=repo, coverage=cov2)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'path': ''}), {'ids': '%d,%d' % (col1.pk, col2.pk)})
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsPatchViewTests(TestCase):
    name = "covmanager:collections_patch"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsPatchApiViewTests(TestCase):
    name = "covmanager:collections_patch_api"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'collectionid': 0, 'patch_revision': 'abc'})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        repo = self.create_repository("hg")
        col = self.create_collection(repository=repo,
                                     coverage=json.dumps({"linesTotal": 1,
                                                          "name": None,
                                                          "coveragePercent": 0.0,
                                                          "children": {"test.c": {"coverage": []}},
                                                          "linesMissed": 1,
                                                          "linesCovered": 0}))
        with open(os.path.join(repo.location, "test.c"), "w") as fp:
            fp.write("hello")
        self.hg(repo, "add", "test.c")
        self.hg(repo, "commit", "-m", "init")
        with open(os.path.join(repo.location, "test.c"), "w") as fp:
            fp.write("world")
        self.hg(repo, "commit", "-m", "update")
        rev = re.match(r"changeset:   1:([0-9a-f]+)", self.hg(repo, "log")).group(1)
        response = self.client.get(reverse(self.name, kwargs={'collectionid': col.pk, 'patch_revision': rev}))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsBrowseViewTests(TestCase):
    name = "covmanager:collections_browse"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'collectionid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'collectionid': 0}))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)


class CollectionsBrowseApiViewTests(TestCase):
    name = "covmanager:collections_browse_api"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'collectionid': 0, 'path': ''})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        repo = self.create_repository("git")
        col = self.create_collection(repository=repo)
        response = self.client.get(reverse(self.name, kwargs={'collectionid': col.pk, 'path': ''}))
        log.debug(response)
        self.assertEqual(response.status_code, httplib.OK)
