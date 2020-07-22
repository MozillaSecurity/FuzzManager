# coding: utf-8
"""Tests for Pools rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import itertools
import datetime
import json
import logging
import pytest
import requests
from django.contrib.auth.models import User
from . import create_pool, create_task


LOG = logging.getLogger("fm.taskmanager.tests.pools.rest")
pytestmark = pytest.mark.usefixtures("taskmanager_test")  # pylint: disable=invalid-name


def test_rest_pools_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = "/taskmanager/rest/pools/"
    assert api_client.get(url).status_code == requests.codes["unauthorized"]
    assert api_client.post(url).status_code == requests.codes["unauthorized"]
    assert api_client.put(url).status_code == requests.codes["unauthorized"]
    assert api_client.patch(url).status_code == requests.codes["unauthorized"]
    assert api_client.delete(url).status_code == requests.codes["unauthorized"]


def test_rest_pools_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username="test-noperm")
    api_client.force_authenticate(user=user)
    url = "/taskmanager/rest/pools/"
    assert api_client.get(url).status_code == requests.codes["forbidden"]
    assert api_client.post(url).status_code == requests.codes["forbidden"]
    assert api_client.put(url).status_code == requests.codes["forbidden"]
    assert api_client.patch(url).status_code == requests.codes["forbidden"]
    assert api_client.delete(url).status_code == requests.codes["forbidden"]


@pytest.mark.parametrize(("method", "item"), itertools.product(["post", "patch", "put", "delete"], [True, False]))
def test_rest_pool_methods(api_client, method, item):
    """post/put/patch/delete should not be allowed"""
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    if item:
        pool = create_pool()
        url = "/taskmanager/rest/pools/%d/" % (pool.pk,)
    else:
        url = "/taskmanager/rest/pools/"

    method = getattr(api_client, method)
    resp = method(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["method_not_allowed"]


@pytest.mark.parametrize("item", [True, False])
def test_rest_pool_read(api_client, item):
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    pool = create_pool()
    if item:
        url = "/taskmanager/rest/pools/%d/" % (pool.pk,)
    else:
        url = "/taskmanager/rest/pools/"

    resp = api_client.get(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    if not item:
        assert set(resp.keys()) == {"count", "previous", "results", "next"}
        assert resp["count"] == 1
        assert resp["previous"] is None
        assert resp["next"] is None
        assert len(resp["results"]) == 1
        resp = resp["results"][0]
    assert set(resp.keys()) == {
        "pool_id", "pool_name", "platform", "size", "cpu", "cycle_time", "id", "running", "status", "max_run_time",
    }
    assert resp["id"] == pool.pk
    assert resp["pool_id"] == pool.pool_id
    assert resp["pool_name"] == pool.pool_name
    assert resp["platform"] == pool.platform
    assert resp["size"] == pool.size
    assert resp["cpu"] == pool.cpu
    assert resp["running"] == 0
    assert resp["status"] == "unknown"
    assert datetime.timedelta(seconds=int(resp["cycle_time"])) == pool.cycle_time


def test_rest_pool_running_status(api_client):
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    pool = create_pool()
    create_task(pool=pool, run_id=1)
    task2 = create_task(pool=pool, run_id=2)
    url = "/taskmanager/rest/pools/%d/" % (pool.pk,)

    resp = api_client.get(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    assert resp["running"] == 2
    assert resp["status"] == "healthy"

    pool.size = 2
    pool.save()
    resp = api_client.get(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    assert resp["running"] == 2
    assert resp["status"] == "healthy"

    task2.state = "not-running"
    task2.save()
    resp = api_client.get(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    assert resp["running"] == 1
    assert resp["status"] == "partial"

    pool.size = 0
    pool.save()
    resp = api_client.get(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    assert resp["running"] == 1
    assert resp["status"] == "disabled"
