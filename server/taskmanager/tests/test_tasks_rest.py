# coding: utf-8
"""Tests for Tasks rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import itertools
import json
import logging
import pytest
import requests
from django.contrib.auth.models import User
from django.utils import dateparse
from taskmanager.models import Task
from . import create_pool, create_task

LOG = logging.getLogger("fm.taskmanager.tests.tasks.rest")
pytestmark = pytest.mark.usefixtures("taskmanager_test")  # pylint: disable=invalid-name


def test_rest_tasks_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = "/taskmanager/rest/tasks/"
    assert api_client.get(url).status_code == requests.codes["unauthorized"]
    assert api_client.post(url).status_code == requests.codes["unauthorized"]
    assert api_client.put(url).status_code == requests.codes["unauthorized"]
    assert api_client.patch(url).status_code == requests.codes["unauthorized"]
    assert api_client.delete(url).status_code == requests.codes["unauthorized"]


def test_rest_tasks_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username="test-noperm")
    api_client.force_authenticate(user=user)
    url = "/taskmanager/rest/tasks/"
    assert api_client.get(url).status_code == requests.codes["forbidden"]
    assert api_client.post(url).status_code == requests.codes["forbidden"]
    assert api_client.put(url).status_code == requests.codes["forbidden"]
    assert api_client.patch(url).status_code == requests.codes["forbidden"]
    assert api_client.delete(url).status_code == requests.codes["forbidden"]


@pytest.mark.parametrize(("method", "item"), itertools.product(["post", "put", "patch", "delete"], [True, False]))
def test_rest_task_methods(api_client, method, item):
    """post/put/patch/delete should not be allowed"""
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    if item:
        pool = create_pool()
        task = create_task(pool=pool)
        url = "/taskmanager/rest/tasks/%d/" % (task.pk,)
    else:
        url = "/taskmanager/rest/tasks/"

    method = getattr(api_client, method)
    resp = method(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["method_not_allowed"]


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_rest_task_status_methods(api_client, method):
    """post/put/patch/delete should not be allowed"""
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    pool = create_pool()
    create_task(pool=pool)
    url = "/taskmanager/rest/tasks/update_status/"

    method = getattr(api_client, method)
    resp = method(url)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["method_not_allowed"]


@pytest.mark.parametrize(
    ("make_data", "result", "status_data"),
    [
        (
            lambda task: {
                "client": "task-%s-run-%s" % (task.task_id, task.run_id),
            },
            requests.codes["bad_request"],
            "Status text",
        ),
        (
            lambda task: {
                "client": "task-%s-run-%s" % (task.task_id, task.run_id),
                "status_data": "Hello world",
                "extra": "blah",
            },
            requests.codes["bad_request"],
            "Status text",
        ),
        (
            lambda task: None,
            requests.codes["bad_request"],
            "Status text",
        ),
        (
            lambda task: {
                "status_data": "Not updated",
            },
            requests.codes["bad_request"],
            "Status text",
        ),
        (
            lambda task: {
                "client": "x",
                "status_data": "Not updated",
            },
            requests.codes["not_found"],
            "Status text",
        ),
        (
            lambda task: {
                "client": "task-%s-run-%s" % (task.task_id, task.run_id),
                "status_data": "Hello world",
            },
            requests.codes["ok"],
            "Hello world",
        ),
    ],
)
def test_rest_task_status(api_client, make_data, result, status_data):
    """post should require well-formed parameters"""
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    pool = create_pool()
    task = create_task(pool=pool)
    url = "/taskmanager/rest/tasks/update_status/"

    resp = api_client.post(url, data=make_data(task))
    LOG.debug(resp)
    assert resp.status_code == result
    task = Task.objects.get(pk=task.pk)
    assert task.status_data == status_data


def test_rest_task_status_unknown(api_client):
    """post should require well-formed parameters"""
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    url = "/taskmanager/rest/tasks/update_status/"

    data = {
        "client": "task-unknown-run-0",
        "status_data": "Hello world",
    }
    resp = api_client.post(url, data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    task = Task.objects.get()
    assert task.status_data == data["status_data"]
    assert task.pool is None


@pytest.mark.parametrize("item", [True, False])
def test_rest_task_read(api_client, item):
    user = User.objects.get(username="test")
    api_client.force_authenticate(user=user)
    pool = create_pool()
    task = create_task(pool=pool)
    if item:
        url = "/taskmanager/rest/tasks/%d/" % (task.pk,)
    else:
        url = "/taskmanager/rest/tasks/"

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
        "task_id", "decision_id", "run_id", "state", "created", "status_data",
        "started", "id", "resolved", "expires", "pool",
    }
    assert resp["id"] == task.pk
    assert resp["pool"] == pool.pk
    assert resp["task_id"] == task.task_id
    assert resp["decision_id"] == task.decision_id
    assert resp["state"] == task.state
    assert dateparse.parse_datetime(resp["created"]) == task.created
    assert resp["status_data"] == task.status_data
    assert dateparse.parse_datetime(resp["started"]) == task.started
    assert dateparse.parse_datetime(resp["resolved"]) == task.resolved
    assert dateparse.parse_datetime(resp["expires"]) == task.expires
    assert resp["run_id"] == task.run_id
