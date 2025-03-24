"""Tests for CrashManager populate_bucket_statistics management command"""

import pytest
from django.core.management import call_command

from crashmanager.models import BucketStatistics

pytestmark = pytest.mark.django_db()


def test_populate_bucket_stats(capsys, cm):
    """Test that bucket statistics are correctly populated"""
    bucket = cm.create_bucket(shortDescription="bucket #1")

    cm.create_crash(
        bucket=bucket,
        tool="tool1",
        testcase=cm.create_testcase("test.txt", quality=5),
    ),
    cm.create_crash(
        bucket=bucket,
        tool="tool1",
        testcase=cm.create_testcase("test2.txt", quality=3),
    )

    call_command("populate_bucket_statistics")

    stats = BucketStatistics.objects.get(bucket=bucket, tool__name="tool1")
    assert stats.size == 2
    assert stats.quality == 3
    assert "Successfully created/updated 1 bucket statistics" in capsys.readouterr().out


def test_populate_bucket_stats_force(capsys, cm):
    """Test that --force flag clears existing statistics"""
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(
        bucket=bucket,
        tool="tool2",
        testcase=cm.create_testcase("test.txt", quality=5),
    )

    # Update to a wrong statistic value for bucket
    BucketStatistics.objects.update_or_create(
        bucket=bucket, tool=crash.tool, defaults={"size": 10, "quality": 1}
    )

    call_command("populate_bucket_statistics", "--force")

    stats = BucketStatistics.objects.get(bucket=bucket, tool=crash.tool)
    assert stats.size == 1
    assert stats.quality == 5
    output = capsys.readouterr().out
    assert "Clearing existing statistics" in output
    assert "Successfully created/updated 1 bucket statistics" in output
