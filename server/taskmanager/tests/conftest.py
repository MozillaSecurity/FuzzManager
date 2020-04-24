# coding: utf-8
'''
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
import pytest
from crashmanager.models import User as cmUser


def _create_user(username, email="test@mozilla.com", password="test", has_permission=True):
    user = User.objects.create_user(username, email, password)
    user.user_permissions.clear()
    if has_permission:
        content_type = ContentType.objects.get_for_model(cmUser)
        perm = Permission.objects.get(content_type=content_type, codename='view_taskmanager')
        user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    user.save()
    return user


@pytest.fixture
def taskmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all taskmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test")
    _create_user("test-noperm", has_permission=False)
