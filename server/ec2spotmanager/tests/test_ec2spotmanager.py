# coding: utf-8
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
from django.urls import reverse
import pytest


LOG = logging.getLogger("fm.ec2spotmanager.tests.ec2spotmanager")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name


def test_ec2spotmanager_index(client):
    """Request of root url redirects to pools view"""
    client.login(username='test', password='test')
    response = client.get(reverse('ec2spotmanager:index'))
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('ec2spotmanager:pools')


def test_ec2spotmanager_logout(client):
    """Logout url actually logs us out"""
    client.login(username='test', password='test')
    index = reverse('ec2spotmanager:pools')
    assert client.get(index).status_code == requests.codes['ok']
    response = client.get(reverse('logout'))
    LOG.debug(response)
    response = client.get(index)
    assert response.status_code == requests.codes['found']
    assert response.url == '/login/?next=' + index


def test_ec2spotmanager_noperm(client):
    """Request without permission results in 403"""
    client.login(username='test-noperm', password='test')
    resp = client.get(reverse('ec2spotmanager:index'))
    assert resp.status_code == 403
