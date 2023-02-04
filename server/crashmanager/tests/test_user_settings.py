"""Tests for usersettings views.

@author:     Eva Bardou

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import logging

import pytest
import requests
from django.test.client import Client
from django.urls import reverse

from crashmanager.models import Tool, User

from .conftest import _cm_result

LOG = logging.getLogger("fm.crashmanager.tests.usersettings")
pytestmark = pytest.mark.usefixtures("crashmanager_test")


def test_user_settings_no_login(client: Client) -> None:
    """Request without login hits the login redirect"""
    path = reverse("crashmanager:usersettings")
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


def test_user_settings_simple_get(client: Client) -> None:
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    path = reverse("crashmanager:usersettings")
    response = client.get(path)
    assert response.status_code == requests.codes["ok"]
    assert list(response.context["bugzilla_providers"]) == []
    assert response.context["user"] == User.objects.get(user__username="test").user


def test_user_settings_edit(client: Client, cm: _cm_result) -> None:
    """No errors are thrown in template"""
    tools = [Tool.objects.create(name="Tool #%d" % (i + 1)) for i in range(2)]
    providers = [
        cm.create_bugprovider(hostname="Provider #%d" % (i + 1)) for i in range(2)
    ]
    [cm.create_template(name="Template #%d" % (i + 1)) for i in range(2)]
    user = User.objects.get(user__username="test")
    assert list(user.defaultToolsFilter.all()) == []
    assert user.defaultProviderId == 1
    assert user.defaultTemplateId == 0
    assert user.user.email == "test@mozilla.com"
    assert not user.inaccessible_bug
    assert not user.bucket_hit
    assert not user.tasks_failed
    client.login(username="test", password="test")
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
            "defaultToolsFilter": [tools[0].pk, tools[1].pk],
            "defaultProviderId": providers[1].pk,
            "defaultTemplateId": 1,
            "email": "mynewemail@mozilla.com",
            "inaccessible_bug": True,
            "bucket_hit": True,
            "tasks_failed": True,
        },
    )
    LOG.debug(response)
    # Redirecting to user settings when the action is successful
    assert response.status_code == requests.codes["found"]
    assert response.url == "/crashmanager/usersettings/"
    user.refresh_from_db()
    assert Tool.objects.count() == 2
    assert list(user.defaultToolsFilter.all()) == list(Tool.objects.all())
    assert user.defaultProviderId == 2
    assert user.defaultTemplateId == 1
    assert user.user.email == "mynewemail@mozilla.com"
    assert user.inaccessible_bug
    assert user.bucket_hit
    assert user.tasks_failed
