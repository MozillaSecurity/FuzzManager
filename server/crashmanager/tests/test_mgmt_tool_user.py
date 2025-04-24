"""Tests for add/remove tool management commands by username

@license:
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from crashmanager.models import Tool
from crashmanager.models import User as CrashManagerUser

pytestmark = pytest.mark.django_db()


def test_add_tool_to_user(capsys):
    """Test adding new tool to user's filter by username"""
    # Create the tool first so it's in the choices list
    Tool.objects.create(name="newtool")
    User.objects.create_user("testuser")

    call_command("add_tool_to_user", "testuser", "newtool")

    # Check command output
    out, _ = capsys.readouterr()
    # No creation message since we pre-created the tool
    assert "added to user" in out

    # Verify database state
    user = User.objects.get(username="testuser")
    cm_user = CrashManagerUser.objects.get(user=user)
    assert cm_user.defaultToolsFilter.filter(name="newtool").exists()


def test_remove_tool_from_user_exists(capsys):
    """Test removing existing tool from filter"""
    user = User.objects.create_user("testuser")
    cm_user = CrashManagerUser.get_or_create_restricted(user)[0]
    tool = Tool.objects.create(name="oldtool")
    cm_user.defaultToolsFilter.add(tool)

    call_command("rm_tool_from_user", "testuser", "oldtool")

    # Check output
    out, _ = capsys.readouterr()
    assert "removed from user" in out
    assert not cm_user.defaultToolsFilter.filter(name="oldtool").exists()


def test_remove_tool_from_user_last_tool(capsys):
    """Test warning when removing last tool"""
    user = User.objects.create_user("testuser")
    cm_user = CrashManagerUser.get_or_create_restricted(user)[0]
    tool = Tool.objects.create(name="lasttool")
    cm_user.defaultToolsFilter.add(tool)

    call_command("rm_tool_from_user", "testuser", "lasttool")

    # Check warning
    out, _ = capsys.readouterr()
    assert "has no tools assigned" in out


def test_remove_tool_from_user_nonexistent(capsys):
    """Test removing non-existent tool shows error"""
    User.objects.create_user("testuser")

    # Create a valid tool first (to avoid the choices validation error)
    Tool.objects.create(name="validtool")

    # The test should pass through to the remove operation
    call_command("rm_tool_from_user", "testuser", "validtool")

    # Check output
    out, _ = capsys.readouterr()

    # It will output the normal removal message even though the tool wasn't assigned
    assert "removed from user" in out

    # Also checks for the message about having no tools
    assert "has no tools assigned" in out

    # Verify no changes to tools
    user = User.objects.get(username="testuser")
    cm_user = CrashManagerUser.objects.get(user=user)
    assert cm_user.defaultToolsFilter.count() == 0


def test_add_tool_to_user_invalid_username(capsys):
    """Test error handling for invalid username"""
    # Create a tool first so it's in the choices list
    Tool.objects.create(name="tool")

    # The command raises CommandError, so we need to catch it
    with pytest.raises(CommandError) as excinfo:
        call_command("add_tool_to_user", "nonexistentuser", "tool")

    # Check that the error message contains the right text
    assert "No user found with username 'nonexistentuser'" in str(excinfo.value)


def test_remove_tool_from_user_invalid_username(capsys):
    """Test error handling for invalid username"""
    # Create a tool first so it's in the choices list
    Tool.objects.create(name="tool")

    with pytest.raises(CommandError) as excinfo:
        call_command("rm_tool_from_user", "nonexistentuser", "tool")

    assert "No user found with username 'nonexistentuser'" in str(excinfo.value)
