import itertools
import os
import shutil
from datetime import timedelta
from tempfile import mkstemp

from celeryconf import app
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import F, Q
from django.db.models.aggregates import Count
from django.utils import timezone

SIGNATURES_ZIP = os.path.realpath(
    os.path.join(getattr(settings, "SIGNATURE_STORAGE", None), "signatures.zip")
)


@app.task(ignore_result=True)
def update_crash_stats():
    from .models import CrashEntry, CrashHit, Tool

    max_history = timedelta(days=getattr(settings, "CRASH_STATS_MAX_HISTORY_DAYS", 14))
    now = timezone.now()
    cur_period = CrashHit.get_period(now)

    try:
        last_run = CrashHit.objects.all().order_by("-lastUpdate")[0].lastUpdate
    except IndexError:
        # no run, go back as far in history as needed
        last_run = cur_period - max_history

    for hours in itertools.count():
        period = CrashHit.get_period(cur_period) - timedelta(hours=hours)
        crashhits_range = CrashHit.objects.select_for_update().filter(
            Q(lastUpdate__gt=period - timedelta(hours=1))
            & Q(lastUpdate__gte=last_run)
            & Q(lastUpdate__lte=period)
        )
        queryset = CrashEntry.objects.filter(
            created__gt=max(period - timedelta(hours=1), last_run), created__lte=period
        )
        tools_breakdown = Tool.objects.filter(crashentry__in=queryset).annotate(
            crashes=Count("crashentry")
        )
        for tool in tools_breakdown:
            with transaction.atomic():
                obj, created = crashhits_range.get_or_create(
                    tool=tool,
                    defaults={
                        "lastUpdate": min(period, now),
                        "count": tool.crashes,
                    },
                )
                if not created:
                    obj.lastUpdate = min(period, now)
                    obj.count = F("count") + tool.crashes
                    obj.save()
        if period <= last_run:
            break
    # trim old stats
    old_cutoff = cur_period - max_history
    CrashHit.objects.filter(lastUpdate__lt=old_cutoff).delete()


@app.task(ignore_result=True)
def bug_update_status():
    call_command("bug_update_status")


@app.task(ignore_result=True)
def cleanup_old_crashes():
    call_command("cleanup_old_crashes")


@app.task(ignore_result=True)
def triage_new_crashes():
    call_command("triage_new_crashes")


@app.task(ignore_result=True)
def export_signatures():
    fd, tmpf = mkstemp(prefix="fm-sigs-", suffix=".zip")
    os.close(fd)
    try:
        call_command("export_signatures", tmpf)
        os.chmod(tmpf, 0o644)
        shutil.copy(tmpf, SIGNATURES_ZIP)
    finally:
        os.unlink(tmpf)


@app.task(ignore_result=True)
def notify_by_email():
    call_command("notify_by_email")
