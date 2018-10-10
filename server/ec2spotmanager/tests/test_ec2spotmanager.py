'''
Tests for EC2SpotManager

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


log = logging.getLogger("fm.ec2spotmanager.tests.ec2spotmanager")  # pylint: disable=invalid-name


class EC2SpotManagerTests(TestCase):

    def test_index(self):
        """Request of root url redirects to pools view"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse('ec2spotmanager:index'))
        log.debug(response)
        self.assertRedirects(response, reverse('ec2spotmanager:pools'))

    def test_logout(self):
        """Logout url actually logs us out"""
        self.client.login(username='test', password='test')
        index = reverse('ec2spotmanager:pools')
        self.assertEqual(self.client.get(index).status_code, requests.codes['ok'])
        response = self.client.get(reverse('logout'))
        log.debug(response)
        response = self.client.get(index)
        self.assertRedirects(response, '/login/?next=' + index)

    def test_noperm(self):
        """Request without permission results in 404"""
        self.client.login(username='test-noperm', password='test')
        resp = self.client.get(reverse('ec2spotmanager:index'))
        assert resp.status_code == 404
