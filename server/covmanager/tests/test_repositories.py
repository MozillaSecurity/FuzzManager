'''
Tests for CovManager repository views

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
from django.core.urlresolvers import reverse

from . import HAVE_GIT, HAVE_HG, TestCase


log = logging.getLogger("fm.covmanager.tests.repos")  # pylint: disable=invalid-name


class RepositoriesViewTests(TestCase):
    name = "covmanager:repositories"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])

    def test_list(self):
        """Repositories are listed"""
        self.client.login(username='test', password='test')
        repos = []
        if HAVE_GIT:
            repos.append(self.create_repository("git", name="gittest1"))
            repos.append(self.create_repository("git", name="gittest2"))
        if HAVE_HG:
            repos.append(self.create_repository("hg", name="hgtest1"))
            repos.append(self.create_repository("hg", name="hgtest2"))
        if not repos:
            pytest.skip("no repositories available")
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertEqual(set(response.context['repositories']), set(repos))


class RepositoriesSearchViewTests(TestCase):
    name = "covmanager:repositories_search_api"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])

    @pytest.mark.skipIf(not HAVE_GIT)
    def test_search_git(self):
        self.create_repository("git", name="gittest1")
        self.create_repository("git", name="gittest2")
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name), {"name": "blah"})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(set(response.keys()), {"results"})
        self.assertEqual(response["results"], [])
        response = self.client.get(reverse(self.name), {"name": "test"})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(set(response.keys()), {"results"})
        self.assertEqual(set(response["results"]), {"gittest1", "gittest2"})

    @pytest.mark.skipIf(not HAVE_HG)
    def test_search_hg(self):
        self.create_repository("hg", name="hgtest1")
        self.create_repository("hg", name="hgtest2")
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name), {"name": "blah"})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(set(response.keys()), {"results"})
        self.assertEqual(response["results"], [])
        response = self.client.get(reverse(self.name), {"name": "test"})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        response = json.loads(response.content.decode('utf-8'))
        self.assertEqual(set(response.keys()), {"results"})
        self.assertEqual(set(response["results"]), {"hgtest1", "hgtest2"})
