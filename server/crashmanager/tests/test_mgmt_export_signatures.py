from __future__ import unicode_literals
import json
import os
import re
import tempfile
import zipfile

import pytest
from django.core.management import call_command, CommandError

from crashmanager.models import Bucket


pytestmark = pytest.mark.django_db(transaction=True)


def test_args():
    with pytest.raises(CommandError, match=r"Error: .* arguments"):
        call_command("export_signatures")


def test_none():
    fd, tmpf = tempfile.mkstemp()
    os.close(fd)
    try:
        call_command("export_signatures", tmpf)
        with zipfile.ZipFile(tmpf) as zipf:
            for member in zipf.infolist():
                raise Exception("expected no members, got %r", member)
    finally:
        os.unlink(tmpf)


def test_some():
    sig1 = Bucket.objects.create(signature='sig1', frequent=True)
    sig2 = Bucket.objects.create(signature='sig2', shortDescription="desc")
    members = set()
    fd, tmpf = tempfile.mkstemp()
    os.close(fd)
    try:
        call_command("export_signatures", tmpf)
        with zipfile.ZipFile(tmpf) as zipf:
            for member in zipf.infolist():
                assert member not in members
                members.add(member)
            assert len(members) == 4
            expected = {"%d.metadata" % sig1.pk,
                        "%d.signature" % sig1.pk,
                        "%d.metadata" % sig2.pk,
                        "%d.signature" % sig2.pk}
            assert {m.filename for m in members} == expected
            for member in members:
                with zipf.open(member) as memberf:
                    contents = memberf.read().decode('utf-8')
                m = re.match(r"^(\d+).(metadata|signature)$", member.filename)
                assert m is not None
                if m.group(2) == "metadata":
                    obj = json.loads(contents)
                    assert set(obj.keys()) == {"shortDescription", "frequent", "size"}
                    assert obj['size'] == 0
                    if int(m.group(1)) == sig1.pk:
                        assert obj['frequent']
                        assert obj['shortDescription'] == ''
                    else:
                        assert not obj['frequent']
                        assert obj['shortDescription'] == 'desc'
                else:
                    if int(m.group(1)) == sig1.pk:
                        assert contents == "sig1"
                    else:
                        assert contents == "sig2"
    finally:
        os.unlink(tmpf)
