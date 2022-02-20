from __future__ import annotations

from django.core.management import call_command

from celeryconf import app
from . import cron  # noqa ensure cron tasks get registered


@app.task(ignore_result=True)
def triage_new_crash(pk: int) -> None:
    call_command('triage_new_crash', pk)
