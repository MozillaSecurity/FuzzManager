# coding: utf-8
'''Tests for CrashManager add_permission management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import pytest
from django.contrib.auth.models import User
from django.core.management import call_command, CommandError


pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name


def test_args():
    with pytest.raises(CommandError, match=r"Error: .*arguments.*"):
        call_command("add_permission")


def test_no_such_user():
    with pytest.raises(User.DoesNotExist):
        call_command("add_permission", "test@example.com", "crashmanager.models.User:view_crashmanager")


def test_no_perms():
    User.objects.create_user("test", "test@example.com", "test")
    with pytest.raises(CommandError, match=r"Error: .*arguments.*"):
        call_command("add_permission", "test")


def test_one_perm():
    user = User.objects.create_user("test", "test@example.com", "test")
    user.user_permissions.clear()  # clear any default permissions
    call_command("add_permission", "test", "crashmanager.models.User:view_crashmanager")
    assert set(user.get_all_permissions()) == {'crashmanager.view_crashmanager'}


def test_two_perms():
    user = User.objects.create_user("test", "test@example.com", "test")
    user.user_permissions.clear()  # clear any default permissions
    call_command("add_permission", "test", "crashmanager.models.User:view_crashmanager",
                 "crashmanager.models.User:view_covmanager")
    assert set(user.get_all_permissions()) == {'crashmanager.view_crashmanager', 'crashmanager.view_covmanager'}
