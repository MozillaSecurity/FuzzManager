"""Common utilities for tests

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.authtoken.models import Token

LOG = logging.getLogger("fm.server.tests")


@pytest.fixture
def auth_client():
    """Create an authenticated client with token"""
    client = Client()
    user = User.objects.create_superuser("test", "test@example.com", "test")
    token = Token.objects.create(user=user)
    return client, token
