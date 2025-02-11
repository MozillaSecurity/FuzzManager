"""Tests for CrashManager rm_permission management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name


def test_args():
    with pytest.raises(CommandError, match=r"Error: .*arguments.*"):
        call_command("rm_permission")


def test_no_such_user():
    with pytest.raises(User.DoesNotExist):
        call_command(
            "rm_permission",
            "test@example.com",
            "view_crashmanager",
        )


def test_no_perms():
    User.objects.create_user("test", "test@example.com", "test")
    with pytest.raises(CommandError, match=r"Error: .*arguments.*"):
        call_command("rm_permission", "test")


def test_rm_perms_from_empty():
    user = User.objects.create_user("test", "test@example.com", "test")
    user.user_permissions.clear()  # clear any default permissions
    call_command("rm_permission", "test", "view_crashmanager")
    assert set(user.get_all_permissions()) == set()


def test_one_perm():
    user = User.objects.create_user("test", "test@example.com", "test")
    call_command("rm_permission", "test", "view_covmanager")
    assert set(user.get_all_permissions()) == {"crashmanager.covmanager_all"}


def test_two_perms():
    user = User.objects.create_user("test", "test@example.com", "test")
    call_command(
        "rm_permission",
        "test",
        "covmanager_all",
        "view_covmanager",
    )
    assert set(user.get_all_permissions()) == set()
