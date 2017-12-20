import json

import pytest
from django.core.management import call_command, CommandError

from crashmanager.models import Bucket, Client, CrashEntry, OS, Platform, Product, Tool


pytestmark = pytest.mark.django_db(transaction=True)


def test_args():
    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("triage_new_crashes", "")


def test_none():
    call_command("triage_new_crashes")


def test_some():
    buckets = [Bucket.objects.create(signature=json.dumps({"symptoms": [
               {'src': 'stderr',
                'type': 'output',
                'value': '/foo/'}]})),
               Bucket.objects.create(signature=json.dumps({"symptoms": [
                   {'src': 'stderr',
                    'type': 'output',
                    'value': '/match/'}]}))]
    defaults = {"client": Client.objects.create(),
                "os": OS.objects.create(),
                "platform": Platform.objects.create(),
                "product": Product.objects.create(),
                "tool": Tool.objects.create()}
    crashes = [CrashEntry.objects.create(bucket=buckets[0], rawStderr="match", **defaults),
               CrashEntry.objects.create(rawStderr="match", **defaults),
               CrashEntry.objects.create(rawStderr="blah", **defaults)]
    for c in crashes:
        assert not c.triagedOnce

    call_command("triage_new_crashes")

    crashes = [CrashEntry.objects.get(pk=c.pk) for c in crashes]

    for c in crashes:
        assert c.triagedOnce

    assert crashes[0].bucket.pk == buckets[0].pk
    assert crashes[1].bucket.pk == buckets[1].pk
    assert crashes[2].bucket is None
