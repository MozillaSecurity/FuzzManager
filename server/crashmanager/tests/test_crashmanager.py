'''
Tests for CrashManager

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
import logging

from django.core.urlresolvers import reverse

from . import TestCase


log = logging.getLogger("fm.crashmanager.tests.crashmanager")


class CrashManagerTests(TestCase):

    def test_redirect(self):
        """Request without login hits the login redirect"""
        self.assertRedirects(self.client.get('/'), '/login/?next=/')

    def test_no_login(self):
        """Request of root url redirects to crashes view"""
        self.client.login(username='test', password='test')
        self.assertRedirects(self.client.get('/'), reverse('crashmanager:crashes'))

    def test_logout(self):
        """Logout url actually logs us out"""
        self.client.login(username='test', password='test')
        self.assertEqual(self.client.get(reverse('crashmanager:crashes')).status_code, httplib.OK)
        self.client.get(reverse('crashmanager:logout'))
        self.assertRedirects(self.client.get('/'), '/login/?next=/')