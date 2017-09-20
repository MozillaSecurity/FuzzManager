'''
Tests for EC2SpotManager

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


log = logging.getLogger("fm.ec2spotmanager.tests.ec2spotmanager")


class EC2SpotManagerTests(TestCase):

    def test_index(self):
        """Request of root url redirects to pools view"""
        self.client.login(username='test', password='test')
        self.assertRedirects(self.client.get(reverse('ec2spotmanager:index')), reverse('ec2spotmanager:pools'))

    def test_logout(self):
        """Logout url actually logs us out"""
        self.client.login(username='test', password='test')
        index = reverse('ec2spotmanager:pools')
        self.assertEqual(self.client.get(index).status_code, httplib.OK)
        self.client.get(reverse('ec2spotmanager:logout'))
        self.assertRedirects(self.client.get(index), '/login/?next=' + index)
