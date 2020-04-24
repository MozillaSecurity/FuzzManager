import datetime
import logging
from django.utils import timezone
from taskmanager.models import Pool, Task


LOG = logging.getLogger("fm.taskmanager.tests")


def create_pool():
    pool = Pool.objects.create(
        pool_id="pool1",
        pool_name="Test Pool",
        platform="linux",
        size=1,
        cpu="x64",
        cycle_time=datetime.timedelta(days=31),
    )
    LOG.debug("Create Pool pk=%d", pool.pk)
    return pool


def create_task(pool=None, task_id="TASK123", run_id=1):
    task_time = timezone.now()
    task = Task.objects.create(
        pool=pool,
        task_id=task_id,
        decision_id="DECISION123",
        run_id=run_id,
        state="running",
        created=task_time,
        status_data="Status text",
        started=task_time + datetime.timedelta(minutes=5),
        resolved=task_time + datetime.timedelta(minutes=10),
        expires=task_time + datetime.timedelta(minutes=15),
    )
    LOG.debug("Create Task pk=%d", task.pk)
    return task
