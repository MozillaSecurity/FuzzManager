from datetime import timedelta
from logging import getLogger
from pathlib import Path
from subprocess import check_output

from celeryconf import app
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from notifications.signals import notify

from . import cron  # noqa ensure cron tasks get registered

LOG = getLogger("taskmanager.tasks")


def get_or_create_pool(worker_type):
    from .models import Pool

    params = {}
    if worker_type in settings.TC_EXTRA_POOLS:
        if "windows" in worker_type:
            platform = "windows"
        elif "macos" in worker_type:
            platform = "macos"
        else:
            platform = "linux"  # default .. change manually if wrong
        pool_id = worker_type
    else:
        if "-pool" not in worker_type:
            # not our task
            return
        platform, pool_id = worker_type.split("-", 1)
        assert pool_id.startswith("pool")
        try:
            params["id"] = int(pool_id[4:])
        except ValueError:
            pass
    params["pool_name"] = pool_id

    pool, created = Pool.objects.get_or_create(
        pool_id=pool_id,
        platform=platform,
        defaults=params,
    )
    if created:
        LOG.info("created new pool %d for %s/%s", pool.id, platform, pool_id)

    return pool


@app.task(ignore_result=True)
def update_pool_defns():
    from fuzzing_decision.common.pool import FuzzingPoolConfig

    from .models import Pool, Task

    # don't remove pools while they have existing tasks
    pools_seen = set(Task.objects.values_list("pool_id", flat=True))

    # get all pools from Github
    storage = Path(settings.TC_FUZZING_CFG_STORAGE)
    if not (storage / ".git").is_dir():
        storage.mkdir(parents=True, exist_ok=True)
        check_output(["git", "init"], cwd=storage)
        check_output(
            [
                "git",
                "remote",
                "add",
                "-t",
                "master",
                "origin",
                settings.TC_FUZZING_CFG_REPO,
            ],
            cwd=storage,
        )
    check_output(
        ["git", "fetch", "-v", "--depth", "1", "origin", "master"],
        cwd=storage,
    )
    check_output(["git", "reset", "--hard", "FETCH_HEAD"], cwd=storage)
    for config_file in storage.glob("pool*.yml"):
        pool_data = list(FuzzingPoolConfig.from_file(config_file))
        defaults = {
            "pool_name": pool_data[0].name,
            "size": sum(pool.tasks for pool in pool_data),
            "cpu": pool_data[0].cpu,
            "cycle_time": timedelta(seconds=pool_data[0].cycle_time),
            "max_run_time": timedelta(seconds=pool_data[0].max_run_time),
        }
        (pool, _created) = Pool.objects.update_or_create(
            pool_id=pool_data[0].config_pool_id,
            platform=pool_data[0].platform,
            defaults=defaults,
        )
        pools_seen.add(pool.id)
        LOG.info(
            "> pool[%d] %s-%s (%s)",
            pool.pk,
            pool.platform,
            pool.pool_id,
            pool.pool_name,
        )

    # if a pool is in the DB but not in Github/TC, it should be deleted
    to_delete = []
    for pool_id in Pool.objects.values_list("id", flat=True):
        if pool_id not in pools_seen:
            to_delete.append(pool_id)
    while to_delete:
        delete_now, to_delete = to_delete[:500], to_delete[500:]
        LOG.warning("deleting pools: %r", delete_now)
        Pool.objects.filter(id__in=delete_now).delete()


@app.task(ignore_result=True)
def task_failed(task_pk):
    from django.contrib.auth.models import User as DjangoUser
    from django.contrib.contenttypes.models import ContentType
    from notifications.models import Notification

    from crashmanager.models import User

    from .models import Pool, Task

    # we got a failed task. maybe generate a notification for this
    # Listing all notifications sent to alert that this pool has failed tasks
    # in the last 24h (not limited by task)
    task = Task.objects.get(pk=task_pk)
    last_day = timezone.now() - timedelta(days=1)
    pool_content_type = ContentType.objects.get_for_model(Pool)
    sent_notification_ids = Notification.objects.filter(
        verb="tasks_failed",
        target_content_type=pool_content_type,
        target_object_id=task.pool.id,
        timestamp__gt=last_day,
    ).values_list("id", flat=True)

    # can't know who is interested in which pool without more info
    # filter by all who have permission to see
    # Excluding users who have already receive this notification
    cm_user_ids = User.objects.filter(
        tasks_failed=True,  # subscribed to these notifications
    ).values_list("user_id", flat=True)
    dj_users = DjangoUser.objects.filter(id__in=cm_user_ids).distinct()

    recipients = dj_users.filter(
        user_permissions__codename="view_taskmanager",
    ).exclude(
        notifications__id__in=sent_notification_ids,
    )

    pool_url = reverse("taskmanager:pool-view-ui", kwargs={"pk": task.pool_id})
    notify.send(
        task,
        recipient=recipients,
        verb="tasks_failed",
        target=task.pool,
        level="warning",
        description=(f"Pool {task.pool.pool_name} has failed tasks. Check {pool_url}"),
    )


@app.task(ignore_result=True)
def update_task(pulse_data):
    import taskcluster

    from .models import Task

    status = pulse_data["status"]
    run_id = pulse_data["runId"]
    run_obj = next(run for run in status["runs"] if run["runId"] == run_id)
    pool = get_or_create_pool(status["workerType"])
    if pool is None:
        LOG.debug(
            "ignoring task %s update for workerType %s",
            status["taskId"],
            status["workerType"],
        )
        return

    defaults = {
        "decision_id": status["taskGroupId"],
        "expires": status["expires"],
        "pool": pool,
        "resolved": run_obj.get("resolved"),
        "started": run_obj.get("started"),
        "state": run_obj["state"],
    }
    task_obj, created = Task.objects.update_or_create(
        task_id=status["taskId"],
        run_id=run_id,
        defaults=defaults,
    )
    LOG.info(
        "%s task %s run %d in pool %s/%s -> %s",
        "created" if created else "updated",
        status["taskId"],
        run_id,
        pool.pool_id,
        pool.platform,
        run_obj["state"],
    )
    if task_obj.created is None:
        # `created` field isn't available via pulse, so get it from Taskcluster
        queue_svc = taskcluster.Queue({"rootUrl": settings.TC_ROOT_URL})
        task = queue_svc.task(status["taskId"])
        Task.objects.filter(id=task_obj.id).update(created=task["created"])
        LOG.info("task %s was created at %s", status["taskId"], task["created"])

    if run_obj["state"] == "failed":
        task_failed.delay(task_obj.id)
