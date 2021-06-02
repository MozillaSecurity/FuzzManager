# coding: utf-8
from __future__ import unicode_literals
import logging
import pytest
import requests
from crashmanager.models import Bug


LOG = logging.getLogger("fm.crashmanager.tests.externalbug.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_externalbug_no_auth(db, api_client, method):
    """must yield unauthorized without authentication"""
    assert getattr(api_client, method)(
        "/crashmanager/rest/crashes/0/external-bug/", {}
    ).status_code == requests.codes['unauthorized']


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
def test_rest_externalbug_no_perm(user_noperm, api_client, method):
    """must yield forbidden without permission"""
    assert getattr(api_client, method)(
        "/crashmanager/rest/crashes/0/external-bug/", {}
    ).status_code == requests.codes['forbidden']


@pytest.mark.parametrize("method, url, user", [
    ("get", "/crashmanager/rest/crashes/0/external-bug/", "normal"),
    ("get", "/crashmanager/rest/crashes/0/external-bug/", "restricted"),
    ("delete", "/crashmanager/rest/crashes/0/external-bug/", "normal"),
    ("delete", "/crashmanager/rest/crashes/0/external-bug/", "restricted"),
    ("patch", "/crashmanager/rest/crashes/0/external-bug/", "normal"),
    ("patch", "/crashmanager/rest/crashes/0/external-bug/", "restricted"),
    ("post", "/crashmanager/rest/crashes/0/external-bug/", "normal"),
    ("post", "/crashmanager/rest/crashes/0/external-bug/", "restricted"),
], indirect=["user"])
def test_rest_externalbug_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['method_not_allowed']


def test_rest_externalbug_update(api_client, cm, user_normal):
    """test that update action create a new Bug and assign it to the crash Bucket"""
    provider = cm.create_bugprovider(hostname="test-provider.com", urlTemplate="test-provider.com/template")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature="crash #1",
                            bucket=bucket,
                            client="client #1",
                            os="os #1",
                            product="product #1",
                            product_version="1",
                            platform="platform #1",
                            tool="tool #1")
    assert not Bug.objects.count()
    resp = api_client.put("/crashmanager/rest/crashes/%d/external-bug/" % crash.pk, {
        "bug_id": "123456",
        "provider": provider.id,
    })
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = resp.json()
    assert resp == {
        "bug_id": "123456",
        "provider": provider.id,
        "details_url": "/crashmanager/signatures/%d/" % bucket.id
    }
    assert Bug.objects.count() == 1
    createdBug = Bug.objects.get()
    assert createdBug.externalId == "123456"
    assert createdBug.externalType == provider
    bucket.refresh_from_db()
    assert bucket.bug == createdBug


def test_rest_externalbug_update_restricted(api_client, cm, user_restricted):
    """test that restricted users cannot perform updates on this endpoint"""
    provider = cm.create_bugprovider(hostname="test-provider.com", urlTemplate="test-provider.com/template")
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature="crash #1",
                            bucket=bucket,
                            client="client #1",
                            os="os #1",
                            product="product #1",
                            product_version="1",
                            platform="platform #1",
                            tool="tool #1")
    resp = api_client.put("/crashmanager/rest/crashes/%d/external-bug/" % crash.pk, {
        "bug_id": "123456",
        "provider": provider.id,
    })
    LOG.debug(resp)
    assert resp.status_code == requests.codes['forbidden']
