'''
Tests for CovManager

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging

from django.core.urlresolvers import reverse

from . import TestCase


log = logging.getLogger("fm.covmanager.tests.covmanager")  # pylint: disable=invalid-name


class CovManagerTests(TestCase):

    def test_index(self):
        """Request of root url redirects to pools view"""
        self.client.login(username='test', password='test')
        self.assertRedirects(self.client.get(reverse('covmanager:index')), reverse('covmanager:collections'))

    def test_noperm(self):
        """Request without permission results in 404"""
        self.client.login(username='test-noperm', password='test')
        resp = self.client.get(reverse('covmanager:index'))
        assert resp.status_code == 404

#url(r'^tools/search/api/$', views.tools_search_api, name="tools_search_api"),
