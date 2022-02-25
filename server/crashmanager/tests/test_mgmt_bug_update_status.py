"""Tests for CrashManager bug_update_status management command

@author:     Eva Bardou

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from notifications.models import Notification
from pytest_mock import MockerFixture

from crashmanager.models import (
    OS,
    Bucket,
    Bug,
    BugProvider,
    Client,
    CrashEntry,
    Platform,
    Product,
    Tool,
)
from crashmanager.models import User as cmUser

pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("crashmanager_test")


def test_args() -> None:
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("bug_update_status", "")


def test_none() -> None:
    call_command("bug_update_status")


@patch(
    "crashmanager.Bugtracker.BugzillaProvider.BugzillaProvider.getBugStatus",
    return_value={"0": None},
)
def test_fake_with_notification(mock_get_bug_status: MockerFixture) -> None:
    provider = BugProvider.objects.create(
        classname="BugzillaProvider", hostname="provider.com", urlTemplate="%s"
    )
    bug = Bug.objects.create(externalId="123456", externalType=provider)
    bucket = Bucket.objects.create(
        bug=bug,
        signature=json.dumps(
            {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
        ),
    )
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    CrashEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)
    user, _ = cmUser.objects.get_or_create(user=User.objects.get(username="test"))
    user.defaultToolsFilter.add(defaults["tool"])
    user.inaccessible_bug = True
    user.save()

    call_command("bug_update_status")

    assert Notification.objects.count() == 1
    notification = Notification.objects.first()
    assert notification.level == "info"
    assert notification.recipient == user.user
    assert notification.unread
    assert notification.actor == bug
    assert notification.verb == "inaccessible_bug"
    assert (
        notification.description
        == f"The bucket {bucket.pk} assigned to the external bug {bug.externalId}"
        f" on {bug.externalType.hostname} has become inaccessible"
    )
    assert notification.target == bug

    # Calling the command again should not generate a duplicate notification
    call_command("bug_update_status")

    assert Notification.objects.count() == 1
