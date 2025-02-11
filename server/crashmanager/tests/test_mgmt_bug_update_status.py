"""Tests for CrashManager bug_update_status management command

@author:     Eva Bardou

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from notifications.models import Notification

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


def test_args():
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("bug_update_status", "")


def test_none():
    call_command("bug_update_status")


@pytest.mark.parametrize("bucket_count", [1, 2])
@patch(
    "crashmanager.Bugtracker.BugzillaProvider.BugzillaProvider.getBugStatus",
    return_value={"0": None},
)
def test_fake_with_notification(mock_get_bug_status, bucket_count):
    provider = BugProvider.objects.create(
        classname="BugzillaProvider", hostname="provider.com", urlTemplate="%s"
    )
    bug = Bug.objects.create(externalId="123456", externalType=provider)
    buckets = []
    defaults = {
        "client": Client.objects.create(),
        "os": OS.objects.create(),
        "platform": Platform.objects.create(),
        "product": Product.objects.create(),
        "tool": Tool.objects.create(),
    }
    for _ in range(bucket_count):
        bucket = Bucket.objects.create(
            bug=bug,
            signature=json.dumps(
                {"symptoms": [{"src": "stderr", "type": "output", "value": "/match/"}]}
            ),
        )
        CrashEntry.objects.create(bucket=bucket, rawStderr="match", **defaults)
        buckets.append(str(bucket.id))
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
    if bucket_count == 1:
        assert (
            notification.description
            == f"The external bug {bug.externalId} on {bug.externalType.hostname} has "
            f"become inaccessible, but is in use by bucket {bucket.pk}"
        )
    else:
        assert (
            notification.description
            == f"The external bug {bug.externalId} on {bug.externalType.hostname} has "
            f"become inaccessible, but is in use by buckets {buckets[0]},{buckets[1]}"
        )
    assert notification.target == bug

    # Calling the command again should not generate a duplicate notification
    call_command("bug_update_status")

    assert Notification.objects.count() == 1
