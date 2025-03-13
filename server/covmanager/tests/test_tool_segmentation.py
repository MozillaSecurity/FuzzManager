"""Tests for tool segmentation feature in Covmanager

@license:
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import json
import pytest
from django.contrib.auth.models import Permission
from rest_framework import status

from crashmanager.models import Tool, Client
from covmanager.models import Repository

pytestmark = pytest.mark.django_db()


@pytest.fixture
def tools():
    return [
        Tool.objects.create(name="tool1"),
        Tool.objects.create(name="tool2"),
        Tool.objects.create(name="tool3"),
    ]


def test_restricted_user_coverage_multiple_tools(
    user_restricted, api_client, cm, tools
):
    # Add base view permission
    view_perm = Permission.objects.get(codename="view_covmanager")
    user_restricted.user_permissions.add(view_perm)

    # Add collection submission permission
    submit_perm = Permission.objects.get(codename="covmanager_submit_collection")
    user_restricted.user_permissions.add(submit_perm)

    # Then create toolfilter and test as before
    cm.create_toolfilter("tool1", user=user_restricted.username)

    coverage_data = {
        "repository": "testrepo",
        "revision": "abc123",
        "branch": "master",
        "tools": "tool1,tool2",
        "coverage": json.dumps(
            {"linesTotal": 1000, "linesCovered": 500, "coveragePercent": 50.0}
        ),
        "client": "testclient",
    }

    response = api_client.post("/covmanager/rest/collections/", coverage_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        "You don't have permission to use the following tools"
        in response.data["message"]
    )


def test_restricted_user_coverage_single_authorized_tool(
    user_restricted, api_client, cm, tools
):
    # Add required permissions
    view_perm = Permission.objects.get(codename="view_covmanager")
    submit_perm = Permission.objects.get(codename="covmanager_submit_collection")
    user_restricted.user_permissions.add(view_perm, submit_perm)

    # Create toolfilter for authorized tool
    cm.create_toolfilter("tool1", user=user_restricted.username)

    # Create required client
    Client.objects.create(name="testclient")

    # Create required repository
    Repository.objects.create(name="testrepo", classname="git")

    coverage_data = {
        "repository": "testrepo",
        "revision": "abc123",
        "branch": "master",
        "tools": "tool1",
        "platform": "x86_64",
        "os": "linux",
        "description": "testdesc",
        "coverage": json.dumps(
            {"linesTotal": 1000, "linesCovered": 500, "coveragePercent": 50.0}
        ),
        "client": "testclient",
    }

    response = api_client.post(
        "/covmanager/rest/collections/", coverage_data, format="json"
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_restricted_user_coverage_single_unauthorized_tool(
    user_restricted, api_client, cm, tools
):
    # Add required permissions
    view_perm = Permission.objects.get(codename="view_covmanager")
    submit_perm = Permission.objects.get(codename="covmanager_submit_collection")
    user_restricted.user_permissions.add(view_perm, submit_perm)

    coverage_data = {
        "repository": "testrepo",
        "revision": "abc123",
        "branch": "master",
        "tools": "tool1",
        "platform": "x86_64",
        "os": "linux",
        "coverage": json.dumps(
            {"linesTotal": 1000, "linesCovered": 500, "coveragePercent": 50.0}
        ),
        "client": "testclient",
    }

    response = api_client.post(
        "/covmanager/rest/collections/", coverage_data, format="json"
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "No tools assigned to user" in response.data["message"]


def test_unrestricted_user_coverage_single_tool(user_normal, api_client, cm, tools):
    # Add required permissions
    view_perm = Permission.objects.get(codename="view_covmanager")
    submit_perm = Permission.objects.get(codename="covmanager_submit_collection")
    user_normal.user_permissions.add(view_perm, submit_perm)

    # Create required client
    Client.objects.create(name="testclient")
    Repository.objects.create(name="testrepo", classname="git")

    coverage_data = {
        "repository": "testrepo",
        "revision": "abc123",
        "branch": "master",
        "tools": "tool2",
        "platform": "x86_64",
        "os": "linux",
        "description": "testdesc",
        "coverage": json.dumps(
            {"linesTotal": 1000, "linesCovered": 500, "coveragePercent": 50.0}
        ),
        "client": "testclient",
    }

    response = api_client.post(
        "/covmanager/rest/collections/", coverage_data, format="json"
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_unrestricted_user_coverage_multiple_tools(user_normal, api_client, cm, tools):
    # Add required permissions
    view_perm = Permission.objects.get(codename="view_covmanager")
    submit_perm = Permission.objects.get(codename="covmanager_submit_collection")
    user_normal.user_permissions.add(view_perm, submit_perm)

    # Create required client
    Client.objects.create(name="testclient")
    Repository.objects.create(name="testrepo", classname="git")

    coverage_data = {
        "repository": "testrepo",
        "revision": "abc123",
        "branch": "master",
        "tools": "tool1,tool3",
        "platform": "x86_64",
        "os": "linux",
        "description": "testdesc",
        "coverage": json.dumps(
            {"linesTotal": 1000, "linesCovered": 500, "coveragePercent": 50.0}
        ),
        "client": "testclient",
    }

    response = api_client.post(
        "/covmanager/rest/collections/", coverage_data, format="json"
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_coverage_missing_tools_parameter(user_normal, api_client, cm, tools):
    """Test error handling when tools parameter is missing"""
    # Add required permissions
    view_perm = Permission.objects.get(codename="view_covmanager")
    submit_perm = Permission.objects.get(codename="covmanager_submit_collection")
    user_normal.user_permissions.add(view_perm, submit_perm)

    # Create required client
    Client.objects.create(name="testclient")
    Repository.objects.create(name="testrepo", classname="git")

    # Missing 'tools' parameter
    coverage_data = {
        "repository": "testrepo",
        "revision": "abc123",
        "branch": "master",
        # "tools" parameter intentionally omitted
        "platform": "x86_64",
        "os": "linux",
        "description": "testdesc",
        "coverage": json.dumps(
            {"linesTotal": 1000, "linesCovered": 500, "coveragePercent": 50.0}
        ),
        "client": "testclient",
    }

    response = api_client.post(
        "/covmanager/rest/collections/", coverage_data, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Missing required 'tools' parameter" in response.data["message"]
