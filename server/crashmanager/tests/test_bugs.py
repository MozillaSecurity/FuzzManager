# coding: utf-8
'''Tests for bugprovider views.

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


LOG = logging.getLogger("fm.crashmanager.tests.bugs")
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


@pytest.mark.parametrize(("name", "kwargs"),
                         [("crashmanager:bugproviders", {}),
                          ("crashmanager:bugprovidercreate", {}),
                          ("crashmanager:bugproviderdel", {'providerId': 0}),
                          ("crashmanager:bugprovideredit", {'providerId': 0}),
                          ("crashmanager:bugproviderview", {'providerId': 0}),
                          ("crashmanager:createbug", {'crashid': 0}),
                          ("crashmanager:createbugcomment", {'crashid': 0}),
                          ("crashmanager:createtemplate", {'providerId': 0}),
                          ("crashmanager:viewtemplate", {'providerId': 0, 'templateId': 0}),
                          ("crashmanager:viewcommenttemplate", {'providerId': 0, 'templateId': 0})])
def test_bug_providers_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=' + path


@pytest.mark.parametrize(("name", "kwargs"),
                         [("crashmanager:bugproviders", {}),
                          ("crashmanager:bugprovidercreate", {}),
                          ("crashmanager:bugproviderdel", {'providerId': 0}),
                          ("crashmanager:bugprovideredit", {'providerId': 0}),
                          ("crashmanager:bugproviderview", {'providerId': 0}),
                          ("crashmanager:createtemplate", {'providerId': 0}),
                          ("crashmanager:viewtemplate", {'providerId': 0, 'templateId': 0, 'mode': 'create'}),
                          ("crashmanager:viewcommenttemplate", {'providerId': 0, 'templateId': 0, 'mode': 'comment'})])
def test_bug_providers_simple_git(client, cm, name, kwargs):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    if 'providerId' in kwargs:
        kwargs['providerId'] = cm.create_bugprovider().pk
    if 'templateId' in kwargs:
        kwargs['templateId'] = cm.create_template().pk
    response = client.get(reverse(name, kwargs=kwargs))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_create_bug_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket()
    crash = cm.create_crash(bucket=bucket)
    prov = cm.create_bugprovider()
    response = client.get(reverse("crashmanager:createbug", kwargs={"crashid": crash.pk}), {'provider': prov.pk})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_create_bug_comment_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    crash = cm.create_crash()
    prov = cm.create_bugprovider()
    response = client.get(reverse("crashmanager:createbugcomment", kwargs={"crashid": crash.pk}), {'provider': prov.pk})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
