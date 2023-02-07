"""Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from django.http.response import HttpResponse
from django.test import SimpleTestCase as DjangoTestCase


def assert_contains(response: HttpResponse, text: str) -> None:
    """Assert that the response was successful, and contains the given text."""

    class _(DjangoTestCase):
        def runTest(self) -> None:
            pass

    _().assertContains(response, text)


def assert_not_contains(response: HttpResponse, text: str) -> None:
    """Assert that the response was successful, and does not contain the given text."""

    class _(DjangoTestCase):
        def runTest(self) -> None:
            pass

    _().assertNotContains(response, text)
