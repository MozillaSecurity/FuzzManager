"""Tests for CrashManager ls_permission management command

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
        call_command("ls_permission")


def test_no_such_user():
    with pytest.raises(User.DoesNotExist):
        call_command(
            "ls_permission",
            "test@example.com",
        )


def test_ls_perm_empty(capsys):
    user = User.objects.create_user("test", "test@example.com", "test")
    user.user_permissions.clear()  # clear any default permissions
    call_command("ls_permission", "test")
    assert set(capsys.readouterr().out.splitlines()) == set()


def test_ls_perm(capsys):
    User.objects.create_user("test", "test@example.com", "test")
    call_command("ls_permission", "test")
    assert {line.split(" ", 1)[0] for line in capsys.readouterr().out.splitlines()} == {
        "view_covmanager",
        "covmanager_all",
    }
