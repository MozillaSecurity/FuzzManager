"""Tests for Token Rate Limiting functionality.

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging

import pytest
import requests
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token

LOG = logging.getLogger("fm.server.tests.token_rate_limiting")
pytestmark = pytest.mark.django_db

RATE_LIMIT_THRESHOLD = 100


@pytest.mark.parametrize(
    ("name"),
    [
        "crashmanager:crashes-list",
        "covmanager:collections-list",
        "ec2spotmanager:configurations-list",
        "crashmanager:buckets-list",
        "covmanager:repositories-list",
        "covmanager:reportconfigurations-list",
        "crashmanager:buckets-list",
        "crashmanager:bugproviders-list",
    ],
)
def test_token_rate_limiting(auth_client, name):
    """Verify rate limiting behavior across protected API endpoints"""
    client, token = auth_client
    headers = {"Authorization": f"Token {token.key}"}
    endpoint = reverse(name)

    response_status_codes = []

    # Send requests until we exceed the rate limit
    for i in range(RATE_LIMIT_THRESHOLD + 1):
        response = client.get(endpoint, format="json", headers=headers)
        response_status_codes.append(response.status_code)
        LOG.debug("Request %d to %s: %d", i + 1, endpoint, response.status_code)

        if i >= RATE_LIMIT_THRESHOLD:
            assert response.status_code == requests.codes["too_many_requests"]
            assert "Retry-After" in response.headers
        else:
            assert response.status_code in [
                requests.codes["ok"],
                requests.codes["created"],
            ]

    # Verify rate limit was hit exactly once
    assert response_status_codes.count(requests.codes["too_many_requests"]) == 1


def test_different_tokens(auth_client):
    """Verify rate limits are independent per token"""
    client, token1 = auth_client

    # Create second user and token
    second_user = User.objects.create_superuser("test2", "test2@example.com", "test2")
    token2 = Token.objects.create(user=second_user)

    headers1 = {"Authorization": f"Token {token1.key}"}
    headers2 = {"Authorization": f"Token {token2.key}"}
    endpoint = reverse("crashmanager:crashes-list")

    # Exhaust rate limit for first token
    for _ in range(RATE_LIMIT_THRESHOLD + 1):
        client.get(endpoint, format="json", headers=headers1)

    # Verify second token is unaffected
    response = client.get(endpoint, format="json", headers=headers2)
    assert response.status_code == requests.codes["ok"]


def test_invalid_token(auth_client):
    """Verify invalid tokens receive immediate unauthorized response"""
    client, _ = auth_client
    headers = {"Authorization": "Token invalid_token"}
    endpoint = reverse("crashmanager:crashes-list")

    response = client.get(endpoint, format="json", headers=headers)
    assert response.status_code == requests.codes["unauthorized"]
