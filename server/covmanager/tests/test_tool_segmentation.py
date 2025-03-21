"""Tests for tool segmentation feature in Covmanager

@license:
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import json

import pytest
from rest_framework import status

from covmanager.models import Repository
from crashmanager.models import Client, Tool

pytestmark = pytest.mark.django_db()


@pytest.fixture
def tools():
    return [
        Tool.objects.get_or_create(name="tool1")[0],
        Tool.objects.get_or_create(name="tool2")[0],
        Tool.objects.get_or_create(name="tool3")[0],
    ]


def test_restricted_user_coverage_multiple_tools(
    covmgr_user_restricted, api_client, covmgr_helper, tools
):
    # Add tool1 to the user's default tool filter
    covmgr_helper.create_toolfilter("tool1", covmgr_user_restricted.username)

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
    covmgr_user_restricted, api_client, covmgr_helper, tools
):
    # Add tool1 to the user's default tool filter
    covmgr_helper.create_toolfilter("tool1", covmgr_user_restricted.username)
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
    covmgr_user_restricted, api_client, tools
):
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


def test_unrestricted_user_coverage_single_tool(covmgr_user_normal, api_client, tools):
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


def test_unrestricted_user_coverage_multiple_tools(
    covmgr_user_normal, api_client, tools
):
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


def test_coverage_missing_tools_parameter(covmgr_user_normal, api_client, tools):
    """Test error handling when tools parameter is missing"""
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
