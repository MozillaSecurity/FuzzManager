import itertools
from datetime import timedelta

from celeryconf import app
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import F, Q
from django.db.models.aggregates import Count
from django.utils import timezone


@app.task(ignore_result=True)
def update_report_stats():
    from .models import ReportEntry, ReportHit, Tool

    max_history = timedelta(days=getattr(settings, "REPORT_STATS_MAX_HISTORY_DAYS", 14))
    now = timezone.now()
    cur_period = ReportHit.get_period(now)

    try:
        last_run = ReportHit.objects.all().order_by("-lastUpdate")[0].lastUpdate
    except IndexError:
        # no run, go back as far in history as needed
        last_run = cur_period - max_history

    for hours in itertools.count():
        period = ReportHit.get_period(cur_period) - timedelta(hours=hours)
        reporthits_range = ReportHit.objects.select_for_update().filter(
            Q(lastUpdate__gt=period - timedelta(hours=1))
            & Q(lastUpdate__gte=last_run)
            & Q(lastUpdate__lte=period)
        )
        queryset = ReportEntry.objects.filter(
            created__gt=max(period - timedelta(hours=1), last_run), created__lte=period
        )
        tools_breakdown = Tool.objects.filter(reportentry__in=queryset).annotate(
            reports=Count("reportentry")
        )
        for tool in tools_breakdown:
            with transaction.atomic():
                obj, created = reporthits_range.get_or_create(
                    tool=tool,
                    defaults={
                        "lastUpdate": min(period, now),
                        "count": tool.reports,
                    },
                )
                if not created:
                    obj.lastUpdate = min(period, now)
                    obj.count = F("count") + tool.reports
                    obj.save()
        if period <= last_run:
            break
    # trim old stats
    old_cutoff = cur_period - max_history
    ReportHit.objects.filter(lastUpdate__lt=old_cutoff).delete()


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
