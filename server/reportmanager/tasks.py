# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import sys

from celeryconf import app
from django.conf import settings
from django.core.management import call_command
from redis import StrictRedis

from . import cron  # noqa ensure cron tasks get registered

if sys.version_info[:2] < (3, 12):
    from server.utils import batched
else:
    from itertools import batched


@app.task(ignore_result=True, serializer="pickle")
def bulk_delete_reports(query, token):
    from .models import ReportEntry

    queryset = ReportEntry.objects.all()
    queryset.query = query

    for chunk in batched(queryset.values_list("id", flat=True), 100):
        ReportEntry.objects.filter(pk__in=tuple(chunk)).delete()
    cache = StrictRedis.from_url(settings.REDIS_URL)
    cache.srem("cm_async_operations", token)


@app.task(ignore_result=True)
def triage_new_report(pk):
    call_command("triage_new_report", pk)
