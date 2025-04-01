"""Tests for usersettings views.

@author:     Eva Bardou

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging

import pytest
import requests
from django.urls import reverse

from crashmanager.models import Tool, User

LOG = logging.getLogger("fm.crashmanager.tests.usersettings")
pytestmark = pytest.mark.usefixtures("crashmanager_test")


def test_user_settings_no_login(client):
    """Request without login hits the login redirect"""
    path = reverse("crashmanager:usersettings")
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


def test_user_settings_simple_get(client):
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    path = reverse("crashmanager:usersettings")
    response = client.get(path)
    assert response.status_code == requests.codes["ok"]
    assert list(response.context["bugzilla_providers"]) == []


def test_user_settings_edit(client, cm, settings):
    """No errors are thrown in template"""
    settings.ALLOW_EMAIL_EDITION = True
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


def test_user_settings_clear_tool_filter(client, cm):
    """tool filter should be clearable"""
    tools = [Tool.objects.create(name="Tool #%d" % (i + 1)) for i in range(2)]
    providers = [
        cm.create_bugprovider(hostname="Provider #%d" % (i + 1)) for i in range(2)
    ]
    [cm.create_template(name="Template #%d" % (i + 1)) for i in range(2)]
    user = User.objects.get(user__username="test")
    user.defaultToolsFilter.add(tools[0])
    user.defaultToolsFilter.add(tools[1])
    user.save()
    client.login(username="test", password="test")
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
            "defaultToolsFilter": [],
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
    assert not list(user.defaultToolsFilter.all())


def test_user_settings_restricted_no_edit_tool_filter(client, cm):
    """restricted user should not be able to edit tool filter"""
    tools = [Tool.objects.create(name="Tool #%d" % (i + 1)) for i in range(2)]
    providers = [
        cm.create_bugprovider(hostname="Provider #%d" % (i + 1)) for i in range(2)
    ]
    [cm.create_template(name="Template #%d" % (i + 1)) for i in range(2)]
    user = User.objects.get(user__username="test-restricted")
    user.defaultToolsFilter.add(tools[0])
    user.save()
    client.login(username="test", password="test")

    # changed tool filter
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
            "defaultToolsFilter": [tools[1].pk],
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
    assert list(user.defaultToolsFilter.all()) == [tools[0]]

    # empty tool filter
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
            "defaultToolsFilter": [],
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
    assert list(user.defaultToolsFilter.all()) == [tools[0]]

    # omitted tool filter
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
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
    assert list(user.defaultToolsFilter.all()) == [tools[0]]


def test_user_settings_no_edit_email(client, cm, settings):
    """settings.ALLOW_EMAIL_EDITION=False disallows editing email"""
    settings.ALLOW_EMAIL_EDITION = False
    tools = [Tool.objects.create(name="Tool #%d" % (i + 1)) for i in range(2)]
    providers = [
        cm.create_bugprovider(hostname="Provider #%d" % (i + 1)) for i in range(2)
    ]
    [cm.create_template(name="Template #%d" % (i + 1)) for i in range(2)]
    user = User.objects.get(user__username="test")
    user.defaultToolsFilter.add(tools[0])
    user.save()
    assert user.user.email == "test@mozilla.com"

    # changed email
    client.login(username="test", password="test")
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
            "defaultToolsFilter": [tools[0].pk],
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
    assert user.user.email == "test@mozilla.com"

    # omitted email
    response = client.post(
        reverse("crashmanager:usersettings"),
        data={
            "defaultToolsFilter": [tools[0].pk],
            "defaultProviderId": providers[1].pk,
            "defaultTemplateId": 1,
            "inaccessible_bug": True,
            "bucket_hit": True,
            "tasks_failed": True,
        },
    )
    LOG.debug(response)
    LOG.debug(response.context)
    # no redirect, form errors
    assert response.status_code == requests.codes["ok"]
    assert "email" in response.context["form_errors"]
    user.refresh_from_db()
    assert user.user.email == "test@mozilla.com"
