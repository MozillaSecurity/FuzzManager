# coding: utf-8
'''Tests for CovManager

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
import pytest
import requests
from django.urls import reverse


LOG = logging.getLogger("fm.covmanager.tests.covmanager")
pytestmark = pytest.mark.usefixtures("covmanager_test")  # pylint: disable=invalid-name


def test_covmanager_index(client):
    """Request of root url redirects to pools view"""
    client.login(username='test', password='test')
    resp = client.get(reverse('covmanager:index'))
    assert resp.status_code == requests.codes["found"]
    assert resp.url == reverse('covmanager:collections')


def test_covmanager_noperm(client):
    """Request without permission results in 403"""
    client.login(username='test-noperm', password='test')
    resp = client.get(reverse('covmanager:index'))
    assert resp.status_code == 403

#url(r'^tools/search/api/$', views.tools_search_api, name="tools_search_api"),
