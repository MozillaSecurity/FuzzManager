"""
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

from typing import cast

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType

from crashmanager.models import User as cmUser


def _create_user(
    username: str,
    email: str = "test@mozilla.com",
    password: str = "test",
    has_permission: bool = True,
    subscribed: bool = True,
) -> User:
    user = cast(User, User.objects.create_user(username, email, password))
    user.user_permissions.clear()
    if has_permission:
        content_type = ContentType.objects.get_for_model(cmUser)
        perm = Permission.objects.get(
            content_type=content_type, codename="view_taskmanager"
        )
        user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    if subscribed:
        user.tasks_failed = True
    user.save()
    return user


@pytest.fixture
def taskmanager_test(db: None) -> None:  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all taskmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test", subscribed=False)
    _create_user("test-noperm", has_permission=False, subscribed=False)
    _create_user("test-sub")
    _create_user("test-sub-noperm", has_permission=False)
