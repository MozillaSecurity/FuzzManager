# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
from logging import getLogger
from django.utils import timezone
from celeryconf import app


LOG = getLogger("taskmanager.cron")


@app.task(ignore_result=True)
def delete_expired():
    from .models import Task

    # if the tasks no longer exist, or are expired, remove them from our DB too
    now = datetime.now(timezone.utc)
    to_delete = list(Task.objects.filter(expires__lte=now).values_list("pk", flat=True))
    while to_delete:
        delete_now, to_delete = to_delete[:500], to_delete[500:]
        LOG.warning("deleting tasks: %r", delete_now)
        Task.objects.filter(id__in=delete_now).delete()
