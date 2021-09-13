# coding: utf-8
from __future__ import unicode_literals
import logging
import pytest
import requests


LOG = logging.getLogger("fm.crashmanager.tests.templates.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize("url", ["/crashmanager/rest/bugzilla/templates/", "/crashmanager/rest/bugzilla/templates/1/"])
def test_rest_templates_no_auth(db, api_client, method, url):
    """must yield unauthorized without authentication"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['unauthorized']


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize("url", ["/crashmanager/rest/bugzilla/templates/", "/crashmanager/rest/bugzilla/templates/1/"])
def test_rest_templates_no_perm(user_noperm, api_client, method, url):
    """must yield forbidden without permission"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['forbidden']


@pytest.mark.parametrize("method, url, user", [
    ("delete", "/crashmanager/rest/bugzilla/templates/", "normal"),
    ("delete", "/crashmanager/rest/bugzilla/templates/", "restricted"),
    ("delete", "/crashmanager/rest/bugzilla/templates/1/", "normal"),
    ("delete", "/crashmanager/rest/bugzilla/templates/1/", "restricted"),
    ("patch", "/crashmanager/rest/bugzilla/templates/", "normal"),
    ("patch", "/crashmanager/rest/bugzilla/templates/", "restricted"),
    ("patch", "/crashmanager/rest/bugzilla/templates/1/", "normal"),
    ("patch", "/crashmanager/rest/bugzilla/templates/1/", "restricted"),
    ("post", "/crashmanager/rest/bugzilla/templates/", "normal"),
    ("post", "/crashmanager/rest/bugzilla/templates/", "restricted"),
    ("post", "/crashmanager/rest/bugzilla/templates/1/", "normal"),
    ("post", "/crashmanager/rest/bugzilla/templates/1/", "restricted"),
    ("put", "/crashmanager/rest/bugzilla/templates/", "normal"),
    ("put", "/crashmanager/rest/bugzilla/templates/", "restricted"),
    ("put", "/crashmanager/rest/bugzilla/templates/1/", "normal"),
    ("put", "/crashmanager/rest/bugzilla/templates/1/", "restricted"),
], indirect=["user"])
def test_rest_templates_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['method_not_allowed']


def _compare_rest_result_to_template(result, template):
    expected_fields = {
        "id", "mode", "name", "comment", "product", "component", "summary", "version",
        "description", "op_sys", "platform", "priority", "severity", "alias", "cc",
        "assigned_to", "qa_contact", "target_milestone", "whiteboard", "keywords",
        "attrs", "security_group", "testcase_filename", "security", "blocks", "dependson",
    }
    assert set(result) == expected_fields
    for key, value in result.items():
        if key == "mode":
            assert value == getattr(template, key).value
        else:
            assert value == getattr(template, key)


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_templates_list(api_client, user, cm):
    """test that list returns the right templates"""
    expected = 4
    templates = [cm.create_template(name="template #%d" % (i + 1),
                                    product="product #%d" % (i + 1),
                                    component="component #%d" % (i + 1),
                                    version="%d" % (i + 1))
                 for i in range(expected)]
    resp = api_client.get("/crashmanager/rest/bugzilla/templates/")
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    assert resp.status_code == requests.codes['ok']
    resp = resp.json()
    assert set(resp) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == expected
    assert resp['next'] is None
    assert resp['previous'] is None
    assert len(resp['results']) == expected
    for result, template in zip(resp['results'], templates[:expected]):
        _compare_rest_result_to_template(result, template)


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_templates_retrieve(api_client, user, cm):
    """test that retrieve returns the right template"""
    expected = 4
    templates = [cm.create_template(name="template #%d" % (i + 1),
                                    product="product #%d" % (i + 1),
                                    component="component #%d" % (i + 1),
                                    version="%d" % (i + 1))
                 for i in range(expected)]
    for template in templates:
        resp = api_client.get("/crashmanager/rest/bugzilla/templates/%d/" % template.pk)
        LOG.debug(resp)
        status_code = resp.status_code
        resp = resp.json()
        assert status_code == requests.codes['ok'], resp['detail']
        _compare_rest_result_to_template(resp, template)
