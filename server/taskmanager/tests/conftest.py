"""
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType

from crashmanager.models import User as cmUser


def _create_user(
    username,
    email="test@mozilla.com",
    password="test",
    permissions=("view_taskmanager", "taskmanager_all"),
    subscribed=True,
):
    user = User.objects.create_user(username, email, password)
    user.user_permissions.clear()
    if permissions:
        content_type = ContentType.objects.get_for_model(cmUser)
        for perm_name in permissions:
            perm = Permission.objects.get(
                content_type=content_type,
                codename=perm_name,
            )
            user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    if subscribed:
        user.tasks_failed = True
    user.save()
    return user


@pytest.fixture
def taskmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all taskmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test", subscribed=False)
    _create_user("test-noperm", permissions=None, subscribed=False)
    _create_user("test-sub")
    _create_user("test-sub-noperm", permissions=None)
    _create_user(
        "test-only-report",
        permissions=("view_taskmanager", "taskmanager_report_status"),
        subscribed=False,
    )
