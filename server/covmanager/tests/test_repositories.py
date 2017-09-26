'''
Tests for CovManager repository views

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


log = logging.getLogger("fm.covmanager.tests.repos")


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
        self.assertEqual(response.status_code, httplib.OK)


#    url(r'^repositories/$', views.repositories, name="repositories"),
#    url(r'^repositories/search/api/$', views.repositories_search_api, name="repositories_search_api"),

