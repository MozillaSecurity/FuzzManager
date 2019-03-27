# coding: utf-8
'''Tests for CrashManager get_auth_token management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import re
from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from rest_framework.authtoken.models import Token
import pytest


pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name


def test_args():
    with pytest.raises(CommandError, match=r"Error: Enter at least one label."):
        call_command("get_auth_token")


def test_no_such_user():
    with pytest.raises(User.DoesNotExist):
        call_command("get_auth_token", "user")


def test_one_user(capsys):
    user = User.objects.create_user("test", "test@example.com", "test")
    call_command("get_auth_token", "test")
    out, _ = capsys.readouterr()
    key = out.strip()
    tkn = Token.objects.get(user=user)
    assert tkn.key == key
    assert re.match(r"^[A-Fa-f0-9]+$", key) is not None
    assert len(key) > 32  # just check that it's reasonably long


def test_two_users(capsys):
    users = (User.objects.create_user("test", "test@example.com", "test"),
             User.objects.create_user("test2", "test2@example.com", "test2"))
    call_command("get_auth_token", "test", "test2")
    out, _ = capsys.readouterr()
    keys = set(out.strip().split())
    assert len(keys) == len(users)
    tkns = set(tkn.key for tkn in Token.objects.all())
    assert tkns == keys
    for key in keys:
        assert re.match(r"^[A-Fa-f0-9]+$", key) is not None
        assert len(key) > 32  # just check that it's reasonably long
