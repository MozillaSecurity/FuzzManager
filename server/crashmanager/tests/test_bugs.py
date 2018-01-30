'''
Tests for bugprovider views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging

import requests
from django.core.urlresolvers import reverse

from . import TestCase


log = logging.getLogger("fm.crashmanager.tests.bugs")  # pytest: disable=invalid-name


class BugProvidersTests(TestCase):
    name = "crashmanager:bugproviders"

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


class CreateBugProvidersTests(TestCase):
    name = "crashmanager:bugprovidercreate"

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


class DeleteBugProvidersTests(TestCase):
    name = "crashmanager:bugproviderdel"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'providerId': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        prov = self.create_bugprovider()
        response = self.client.get(reverse(self.name, kwargs={'providerId': prov.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class EditBugProvidersTests(TestCase):
    name = "crashmanager:bugprovideredit"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'providerId': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        prov = self.create_bugprovider()
        response = self.client.get(reverse(self.name, kwargs={'providerId': prov.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class ViewBugProvidersTests(TestCase):
    name = "crashmanager:bugproviderview"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'providerId': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        prov = self.create_bugprovider()
        response = self.client.get(reverse(self.name, kwargs={'providerId': prov.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class CreateBugTests(TestCase):
    name = "crashmanager:createbug"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'crashid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket()
        crash = self.create_crash(bucket=bucket)
        prov = self.create_bugprovider()
        response = self.client.get(reverse(self.name, kwargs={"crashid": crash.pk}), {'provider': prov.pk})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class CreateBugCommentTests(TestCase):
    name = "crashmanager:createbugcomment"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'crashid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        crash = self.create_crash()
        prov = self.create_bugprovider()
        response = self.client.get(reverse(self.name, kwargs={"crashid": crash.pk}), {'provider': prov.pk})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class CreateBugTemplateTests(TestCase):
    name = "crashmanager:createtemplate"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'providerId': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        prov = self.create_bugprovider()
        response = self.client.get(reverse(self.name, kwargs={'providerId': prov.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class EditBugTemplateTests(TestCase):
    name = "crashmanager:viewtemplate"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'providerId': 0, 'templateId': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        prov = self.create_bugprovider()
        temp = self.create_template()
        response = self.client.get(reverse(self.name, kwargs={'providerId': prov.pk,
                                                              'templateId': temp.pk,
                                                              'mode': 'create'}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class EditBugCommentTemplateTests(TestCase):
    name = "crashmanager:viewcommenttemplate"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'providerId': 0, 'templateId': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        prov = self.create_bugprovider()
        temp = self.create_template()
        response = self.client.get(reverse(self.name, kwargs={'providerId': prov.pk,
                                                              'templateId': temp.pk,
                                                              'mode': 'comment'}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
