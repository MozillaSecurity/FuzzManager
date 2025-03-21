"""Tests for add/remove tool management commands by username

@license:
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from crashmanager.models import Tool
from crashmanager.models import User as CrashManagerUser

pytestmark = pytest.mark.django_db()


def test_add_tool_to_user_new_tool(capsys):
    """Test adding new tool to user's filter by username"""
    User.objects.create_user("testuser")

    call_command("add_tool_to_user", "testuser", "newtool")

    # Check command output
    out, _ = capsys.readouterr()
    assert "Tool 'newtool' was created." in out
    assert "added to user" in out

    # Verify database state
    user = User.objects.get(username="testuser")
    cm_user = CrashManagerUser.objects.get(user=user)
    assert cm_user.restricted is True
    assert cm_user.defaultToolsFilter.filter(name="newtool").exists()


def test_add_tool_to_user_existing_tool(capsys):
    """Test adding existing tool doesn't recreate it"""
    # Create tool first
    Tool.objects.create(name="existingtool")

    User.objects.create_user("testuser")

    call_command("add_tool_to_user", "testuser", "existingtool")

    # Check command output
    out, _ = capsys.readouterr()
    assert "Tool 'existingtool' was created." not in out
    assert "added to user" in out


def test_add_tool_to_user_restricts_user(capsys):
    """Test unrestricted user becomes restricted when adding tool"""
    user = User.objects.create_user("testuser")
    cm_user = CrashManagerUser.get_or_create_restricted(user)[0]
    cm_user.restricted = False
    cm_user.save()

    call_command("add_tool_to_user", "testuser", "newtool")

    # Check warning message
    out, _ = capsys.readouterr()
    assert "has been restricted for security" in out

    # Verify restriction
    cm_user.refresh_from_db()
    assert cm_user.restricted is True


def test_remove_tool_from_user_exists(capsys):
    """Test removing existing tool from filter"""
    user = User.objects.create_user("testuser")
    cm_user = CrashManagerUser.get_or_create_restricted(user)[0]
    tool = Tool.objects.create(name="oldtool")
    cm_user.defaultToolsFilter.add(tool)

    call_command("remove_tool_from_user", "testuser", "oldtool")

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

    call_command("remove_tool_from_user", "testuser", "lasttool")

    # Check warning
    out, _ = capsys.readouterr()
    assert "has no tools assigned" in out

    # Refresh from DB to get updated restriction status
    cm_user.refresh_from_db()
    assert cm_user.restricted is True


def test_remove_tool_from_user_nonexistent(capsys):
    """Test removing non-existent tool shows error"""
    User.objects.create_user("testuser")

    # Should return normally with error message
    call_command("remove_tool_from_user", "testuser", "notexist")

    # Verify error message
    out, _ = capsys.readouterr()
    assert "Error: Tool 'notexist' is not present in the database" in out

    # Verify no changes to tools
    user = User.objects.get(username="testuser")
    cm_user = CrashManagerUser.objects.get(user=user)
    assert cm_user.defaultToolsFilter.count() == 0


def test_add_tool_to_user_invalid_username(capsys):
    """Test error handling for invalid username"""
    call_command("add_tool_to_user", "nonexistentuser", "tool")
    out, _ = capsys.readouterr()
    assert "No user found with username 'nonexistentuser'" in out


def test_remove_tool_from_user_invalid_username(capsys):
    """Test error handling for invalid username"""
    call_command("remove_tool_from_user", "nonexistentuser", "tool")
    out, _ = capsys.readouterr()
    assert "No user found with username 'nonexistentuser'" in out
