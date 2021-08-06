# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
from logging import getLogger
from django.conf import settings
from django.db.models import Max
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

    task_status = {}
    done = set()

    def _update_task_run(task_id, run_id):
        if (task_id, run_id) in done:
            return

        if task_id not in task_status:
            task_status[task_id] = queue_svc.status(task_id)
        status = task_status[task_id]

        data = dict(status)
        data["runId"] = run_id
        update_task.delay(data)
        done.add((task_id, run_id))

    for task_obj in Task.objects.filter(state__in=["pending", "running"]).select_related("pool"):

        if task_obj.state == "running" and task_obj.created is not None and task_obj.pool is not None:
            if task_obj.created + task_obj.pool.max_run_time >= now:
                continue

        _update_task_run(task_obj.task_id, task_obj.run_id)

    # if there are any tasks with multiple run ids, only the latest one is relevant
    # select all lower runs that are still pending/running and update them
    for result in Task.objects.filter(run_id__gt=0).values('task_id').annotate(latest_run=Max('run_id')):
        task_id = result["task_id"]
        max_run_id = result["latest_run"]

        for task_obj in Task.objects.filter(task_id=task_id, run_id__lt=max_run_id, state__in=["pending", "running"]):
            _update_task_run(task_id, task_obj.run_id)


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
