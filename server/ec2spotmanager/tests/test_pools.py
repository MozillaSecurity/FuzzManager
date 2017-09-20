'''
Tests for Pool views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
import json
import logging

from django.core.urlresolvers import reverse

from . import TestCase


log = logging.getLogger("fm.ec2spotmanager.tests.pools")


class PoolsViewTests(TestCase):
    name = "ec2spotmanager:pools"
    entries_fmt = "Displaying all %d instance pools:"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_no_pools(self):
        """If no pools in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        poollist = response.context['poollist']
        self.assertEqual(len(poollist), 0)  # 0 pools
        self.assertContains(response, self.entries_fmt % 0)
