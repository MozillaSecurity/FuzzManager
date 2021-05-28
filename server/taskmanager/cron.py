# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
from logging import getLogger
from django.conf import settings
from django.utils import timezone
from celeryconf import app


LOG = getLogger("taskmanager.cron")


@app.task(ignore_result=True)
def update_tasks():
    import taskcluster
    from .models import Task
    from .tasks import update_task

    queue_svc = taskcluster.Queue({"rootUrl": settings.TC_ROOT_URL})
    now = datetime.now(timezone.utc)

    # this should never be required, but we seem to miss Task events
    # in mozilla pulse sometimes.
    # if we notice that a task is pending or running for longer than
    # normal, try to update the task directly from taskcluster

    for task_obj in Task.objects.filter(state__in=["pending", "running"]).select_related("pool"):
        if task_obj.state == "running" and task_obj.created is not None and task_obj.pool is not None:
            if task_obj.created + task_obj.pool.max_run_time >= now:
                continue

        status = queue_svc.status(task_obj.task_id)
        status["runId"] = task_obj.run_id
        update_task.delay(status)


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
