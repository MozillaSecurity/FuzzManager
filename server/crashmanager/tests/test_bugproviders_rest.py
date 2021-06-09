# coding: utf-8
from __future__ import unicode_literals
import logging
import pytest
import requests


LOG = logging.getLogger("fm.crashmanager.tests.bugproviders.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_bugproviders_no_auth(db, api_client, method):
    """must yield unauthorized without authentication"""
    assert getattr(api_client, method)(
        "/crashmanager/rest/bugproviders/", {}
    ).status_code == requests.codes['unauthorized']


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_bugproviders_no_perm(user_noperm, api_client, method):
    """must yield forbidden without permission"""
    assert getattr(api_client, method)(
        "/crashmanager/rest/bugproviders/", {}
    ).status_code == requests.codes['forbidden']


@pytest.mark.parametrize("method, url, user", [
    ("delete", "/crashmanager/rest/bugproviders/", "normal"),
    ("delete", "/crashmanager/rest/bugproviders/", "restricted"),
    ("patch", "/crashmanager/rest/bugproviders/", "normal"),
    ("patch", "/crashmanager/rest/bugproviders/", "restricted"),
    ("post", "/crashmanager/rest/bugproviders/", "normal"),
    ("post", "/crashmanager/rest/bugproviders/", "restricted"),
    ("put", "/crashmanager/rest/bugproviders/", "normal"),
    ("put", "/crashmanager/rest/bugproviders/", "restricted"),
], indirect=["user"])
def test_rest_bugproviders_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['method_not_allowed']


@pytest.mark.parametrize("method, url, user", [
    ("get", "/crashmanager/rest/bugproviders/1/", "normal"),
    ("get", "/crashmanager/rest/bugproviders/1/", "restricted"),
    ("delete", "/crashmanager/rest/bugproviders/1/", "normal"),
    ("delete", "/crashmanager/rest/bugproviders/1/", "restricted"),
    ("patch", "/crashmanager/rest/bugproviders/1/", "normal"),
    ("patch", "/crashmanager/rest/bugproviders/1/", "restricted"),
    ("post", "/crashmanager/rest/bugproviders/1/", "normal"),
    ("post", "/crashmanager/rest/bugproviders/1/", "restricted"),
    ("put", "/crashmanager/rest/bugproviders/1/", "normal"),
    ("put", "/crashmanager/rest/bugproviders/1/", "restricted"),
], indirect=["user"])
def test_rest_bugproviders_methods_not_found(api_client, user, method, url):
    """must yield not-found for undeclared methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['not_found']


def _compare_rest_result_to_bugprovider(result, provider):
    expected_fields = {"id", "classname", "hostname", "urlTemplate"}
    assert set(result) == expected_fields
    for key, value in result.items():
        assert value == getattr(provider, key)


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
def test_rest_bugproviders_list(api_client, user, cm):
    """test that list returns the right bug providers"""
    expected = 4
    providers = [cm.create_bugprovider(hostname="test-provider%d.com" % (i + 1),
                                       urlTemplate="test-provider%d.com/template" % (i + 1))
                 for i in range(expected)]
    resp = api_client.get("/crashmanager/rest/bugproviders/")
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = resp.json()
    assert set(resp) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == expected
    assert resp['next'] is None
    assert resp['previous'] is None
    assert len(resp['results']) == expected
    for result, provider in zip(resp['results'], providers[:expected]):
        _compare_rest_result_to_bugprovider(result, provider)
