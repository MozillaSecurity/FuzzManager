"""Tests for bugprovider views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import logging

import pytest
import requests
from django.urls import reverse

from reportmanager.models import BugzillaTemplate

LOG = logging.getLogger("fm.reportmanager.tests.bugs")
pytestmark = pytest.mark.usefixtures("reportmanager_test")


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("reportmanager:bugproviders", {}),
        ("reportmanager:bugprovidercreate", {}),
        ("reportmanager:bugproviderdel", {"providerId": 0}),
        ("reportmanager:bugprovideredit", {"providerId": 0}),
        ("reportmanager:bugproviderview", {"providerId": 0}),
        ("reportmanager:createbug", {"reportid": 0}),
        ("reportmanager:createbugcomment", {"reportid": 0}),
    ],
)
def test_bug_providers_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("reportmanager:templates", {}),
        ("reportmanager:templatecreatebug", {}),
        ("reportmanager:templatecreatecomment", {}),
        ("reportmanager:templateedit", {"templateId": 0}),
        ("reportmanager:templatedup", {"templateId": 0}),
        ("reportmanager:templatedel", {"templateId": 0}),
    ],
)
def test_bugzilla_templates_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes["found"]
    assert resp.url == "/login/?next=" + path


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("reportmanager:bugproviders", {}),
        ("reportmanager:bugprovidercreate", {}),
        ("reportmanager:bugproviderdel", {"providerId": 0}),
        ("reportmanager:bugprovideredit", {"providerId": 0}),
        ("reportmanager:bugproviderview", {"providerId": 0}),
    ],
)
def test_bug_providers_simple_get(client, cm, name, kwargs):
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    if "providerId" in kwargs:
        kwargs["providerId"] = cm.create_bugprovider().pk
    response = client.get(reverse(name, kwargs=kwargs))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("reportmanager:templates", {}),
        ("reportmanager:templatecreatebug", {}),
        ("reportmanager:templatecreatecomment", {}),
        ("reportmanager:templateedit", {"templateId": 0}),
        ("reportmanager:templatedel", {"templateId": 0}),
    ],
)
def test_bugzilla_templates_simple_get(client, cm, name, kwargs):
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    if "templateId" in kwargs:
        kwargs["templateId"] = cm.create_template().pk
    response = client.get(reverse(name, kwargs=kwargs))
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_template_edit(client, cm):
    """No errors are thrown in template"""
    pk = cm.create_template().pk
    assert len(BugzillaTemplate.objects.all()) == 1
    template = BugzillaTemplate.objects.get()
    assert template.mode.value == "bug"
    assert template.name == ""
    assert template.product == ""
    assert template.component == ""
    assert template.version == ""
    client.login(username="test", password="test")
    response = client.post(
        reverse("reportmanager:templateedit", kwargs={"templateId": pk}),
        data={
            "mode": "bug",
            "name": "My bug template",
            "product": "Test product",
            "component": "Test component",
            "version": "1.0",
            "summary": "",
            "description": "",
            "whiteboard": "",
            "keywords": "",
            "op_sys": "",
            "platform": "",
            "priority": "",
            "severity": "",
            "alias": "",
            "cc": "",
            "assigned_to": "",
            "qa_contact": "",
            "target_milestone": "",
            "attrs": "",
            "security": False,
            "security_group": "",
            "testcase_filename": "",
            "comment": "",
            "blocks": "",
            "dependson": "",
        },
    )
    LOG.debug(response)
    # Redirecting to template list when the action is successful
    assert response.status_code == requests.codes["found"]
    assert response.url == "/reportmanager/bugzilla/templates/"
    assert len(BugzillaTemplate.objects.all()) == 1
    template = BugzillaTemplate.objects.get()
    assert template.mode.value == "bug"
    assert template.name == "My bug template"
    assert template.product == "Test product"
    assert template.component == "Test component"
    assert template.version == "1.0"


def test_template_dup(client, cm):
    """No errors are thrown in template"""
    pk = cm.create_template().pk
    assert len(BugzillaTemplate.objects.all()) == 1
    client.login(username="test", password="test")
    response = client.delete(
        reverse("reportmanager:templatedup", kwargs={"templateId": pk})
    )
    LOG.debug(response)
    # Redirecting to template list when the action is successful
    assert response.status_code == requests.codes["found"]
    assert response.url == "/reportmanager/bugzilla/templates/"
    assert len(BugzillaTemplate.objects.all()) == 2
    template = BugzillaTemplate.objects.get(pk=pk)
    clone = BugzillaTemplate.objects.get(pk=pk + 1)
    assert "Clone of " + template.name == clone.name
    for field in (
        "mode",
        "product",
        "component",
        "version",
        "summary",
        "description",
        "whiteboard",
        "keywords",
        "op_sys",
        "platform",
        "priority",
        "severity",
        "alias",
        "cc",
        "assigned_to",
        "qa_contact",
        "target_milestone",
        "attrs",
        "security",
        "security_group",
        "testcase_filename",
        "comment",
    ):
        assert getattr(template, field) == getattr(clone, field)


def test_template_del(client, cm):
    """No errors are thrown in template"""
    pk = cm.create_template().pk
    assert len(BugzillaTemplate.objects.all()) == 1
    client.login(username="test", password="test")
    response = client.delete(
        reverse("reportmanager:templatedel", kwargs={"templateId": pk})
    )
    LOG.debug(response)
    # Redirecting to template list when the action is successful
    assert response.status_code == requests.codes["found"]
    assert response.url == "/reportmanager/bugzilla/templates/"
    assert len(BugzillaTemplate.objects.all()) == 0


def test_template_create_bug_post(client, cm):
    """No errors are thrown in template"""
    assert len(BugzillaTemplate.objects.all()) == 0
    client.login(username="test", password="test")
    response = client.post(
        reverse("reportmanager:templatecreatebug"),
        data={
            "name": "My bug template",
            "product": "Test product",
            "component": "Test component",
            "version": "1.0",
        },
    )
    LOG.debug(response)
    # Redirecting to template list when the action is successful
    assert response.status_code == requests.codes["found"]
    assert response.url == "/reportmanager/bugzilla/templates/"
    assert len(BugzillaTemplate.objects.all()) == 1
    template = BugzillaTemplate.objects.get()
    assert template.mode.value == "bug"
    assert template.name == "My bug template"
    assert template.product == "Test product"
    assert template.component == "Test component"
    assert template.version == "1.0"


def test_template_create_comment_post(client, cm):
    """No errors are thrown in template"""
    assert len(BugzillaTemplate.objects.all()) == 0
    client.login(username="test", password="test")
    response = client.post(
        reverse("reportmanager:templatecreatecomment"),
        data={"name": "My comment template", "comment": "A comment"},
    )
    LOG.debug(response)
    # Redirecting to template list when the action is successful
    assert response.status_code == requests.codes["found"]
    assert response.url == "/reportmanager/bugzilla/templates/"
    assert len(BugzillaTemplate.objects.all()) == 1
    template = BugzillaTemplate.objects.get()
    assert template.mode.value == "comment"
    assert template.name == "My comment template"
    assert template.comment == "A comment"


def test_create_external_bug_simple_get(client, cm):
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    bucket = cm.create_bucket()
    report = cm.create_report(bucket=bucket)
    prov = cm.create_bugprovider()
    response = client.get(
        reverse("reportmanager:createbug", kwargs={"reportid": report.pk}),
        {"provider": prov.pk},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]


def test_create_external_bug_comment_simple_get(client, cm):
    """No errors are thrown in template"""
    client.login(username="test", password="test")
    report = cm.create_report()
    prov = cm.create_bugprovider()
    response = client.get(
        reverse("reportmanager:createbugcomment", kwargs={"reportid": report.pk}),
        {"provider": prov.pk},
    )
    LOG.debug(response)
    assert response.status_code == requests.codes["ok"]
