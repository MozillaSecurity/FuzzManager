# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta
from itertools import count

from celeryconf import app
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone


@app.task(ignore_result=True)
def update_report_stats():
    from .models import ReportEntry, ReportHit

    max_history = timedelta(days=getattr(settings, "REPORT_STATS_MAX_HISTORY_DAYS", 14))
    now = timezone.now()
    cur_period = ReportHit.get_period(now)

    try:
        last_run = ReportHit.objects.all().order_by("-last_update")[0].last_update
    except IndexError:
        # no run, go back as far in history as needed
        last_run = cur_period - max_history

    for hours in count():
        period = ReportHit.get_period(cur_period) - timedelta(hours=hours)
        reporthits_range = ReportHit.objects.select_for_update().filter(
            Q(last_update__gt=period - timedelta(hours=1))
            & Q(last_update__gte=last_run)
            & Q(last_update__lte=period)
        )
        hits = ReportEntry.objects.filter(
            created__gt=max(period - timedelta(hours=1), last_run), created__lte=period
        ).count()

        with transaction.atomic():
            obj, created = reporthits_range.get_or_create(
                defaults={
                    "last_update": min(period, now),
                    "count": hits,
                },
            )
            if not created:
                obj.last_update = min(period, now)
                obj.count = F("count") + hits
                obj.save()
        if period <= last_run:
            break
    # trim old stats
    old_cutoff = cur_period - max_history
    ReportHit.objects.filter(last_update__lt=old_cutoff).delete()


@app.task(ignore_result=True)
def bug_update_status():
    call_command("bug_update_status")


@app.task(ignore_result=True)
def cleanup_old_reports():
    call_command("cleanup_old_reports")


@app.task(ignore_result=True)
def triage_new_reports():
    call_command("triage_new_reports")


@app.task(ignore_result=True)
def notify_by_email():
    call_command("notify_by_email")
