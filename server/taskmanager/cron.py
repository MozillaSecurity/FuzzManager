# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import functools
import logging
try:
    import pathlib
except ImportError:
    pass
import subprocess
from django.conf import settings
from celeryconf import app


LOG = logging.getLogger("taskmanager.cron")


def paginated(func, result_key):
    """Wraps a Taskcluster API that returns a result like:
    {
       continuationToken: "",
       result_key: [...]
    }

    This hides the process of re-requesting with continuationToken,
    and yields the contents of `result_key`
    """
    @functools.wraps(func)
    def _wrapped(*args, **kwds):
        kwds = kwds.copy()
        result = func(*args, **kwds)
        while result.get("continuationToken"):
            for sub in result[result_key]:
                yield sub
            kwds.setdefault("query", {})
            kwds["query"]["continuationToken"] = result["continuationToken"]
            result = func(*args, **kwds)
        for sub in result[result_key]:
            yield sub
    return _wrapped


@app.task(ignore_result=True)
def update_pools():
    """This should look at both Github & Taskcluster and update the database.
    """
    import taskcluster
    from fuzzing_tc.common.pool import PoolConfiguration
    from .models import Pool, Task

    pools_seen = set()  # (platform, fuzzing_id)
    tasks_seen = set()  # (db_id)

    # get all pools/tasks from Taskcluster
    hooks_svc = taskcluster.Hooks({"rootUrl": settings.TC_ROOT_URL})
    queue_svc = taskcluster.Queue({"rootUrl": settings.TC_ROOT_URL})

    def update_task_group(task_group_id):
        for task in paginated(queue_svc.listTaskGroup, "tasks")(task_group_id):
            # the task group id is for the decision
            # we only care about fuzzing tasks
            if task["status"]["taskId"] == task_group_id:
                continue
            for run in task["status"]["runs"]:
                task, _ = Task.objects.get_or_create(
                    pool=pool,
                    decision_id=task_group_id,
                    task_id=task["status"]["taskId"],
                    run_id=run["runId"],
                    defaults={
                        "created": task["task"]["created"],
                        "state": run["state"],
                        "started": run.get("started"),
                        "resolved": run["resolved"],
                        "expires": task["task"]["expires"],
                    },
                )
                LOG.info(
                    ">>> task[%d] %s (run %d)",
                    task.pk,
                    task.task_id,
                    task.run_id,
                )
                tasks_seen.add(task.pk)

    # check last fires from the hook
    hook_group_id = "project-" + settings.TC_PROJECT
    for hook in hooks_svc.listHooks(hook_group_id)["hooks"]:
        hook = hook["hookId"]
        platform, id_ = hook.split("-", 1)
        pool, _ = Pool.objects.get_or_create(
            pool_id=id_,
            platform=platform,
            defaults={"pool_name": hook},
        )
        LOG.info("> pool[%d] %s (%s)", pool.pk, hook, pool.pool_name)
        pools_seen.add((platform, id_))
        for fire in hooks_svc.listLastFires(hook_group_id, hook)["lastFires"]:
            LOG.info("%r", fire)
            if fire["result"] != "success":
                continue
            update_task_group(fire["taskId"])

    # check all tasks that are in the DB, but no longer listed by "listLastFires"
    # .distinct() would be better, but not supported by sqlite?? (for testing)
    for decision in set(Task.objects
                        .exclude(id__in=tasks_seen)
                        .values_list("decision_id", flat=True)):
        update_task_group(decision)

    # if the tasks no longer exist, remove them from our DB too
    to_delete = list(Task.objects.exclude(id__in=tasks_seen).values_list("pk", flat=True))
    while to_delete:
        delete_now, to_delete = to_delete[:500], to_delete[500:]
        LOG.warning("deleting tasks: %r", delete_now)
        Task.objects.filter(id__in=delete_now).delete()

    # get all pools from Github
    storage = pathlib.Path(settings.TC_FUZZING_CFG_STORAGE)
    if not (storage / ".git").is_dir():
        storage.mkdir(parents=True, exist_ok=True)
        subprocess.check_output(["git", "init"], cwd=storage)
        subprocess.check_output(
            ["git", "remote", "add", "-t", "master", "origin", settings.TC_FUZZING_CFG_REPO],
            cwd=storage,
        )
    subprocess.check_output(
        ["git", "fetch", "-v", "--depth", "1", "origin", "master"],
        cwd=storage,
    )
    subprocess.check_output(["git", "reset", "--hard", "FETCH_HEAD"], cwd=storage)
    for config_file in storage.glob("pool*.yml"):
        pool_data = PoolConfiguration.from_file(config_file)
        (pool, created) = Pool.objects.get_or_create(
            pool_id=pool_data.pool_id,
            platform=pool_data.platform,
            defaults={
                "pool_name": pool_data.name,
                "size": pool_data.tasks,
                "cpu": pool_data.cpu,
                "cycle_time": datetime.timedelta(seconds=pool_data.cycle_time),
            },
        )
        if not created:
            pool.pool_name = pool_data.name
            pool.size = pool_data.tasks
            pool.cpu = pool_data.cpu
            pool.cycle_time = datetime.timedelta(seconds=pool_data.cycle_time)
            pool.save()
        pools_seen.add((pool_data.platform, pool_data.pool_id))
        LOG.info("> pool[%d] %s-%s (%s)", pool.pk, pool.platform, pool.pool_id, pool.pool_name)

    # if a pool is in the DB but not in Github/TC, it should be deleted
    to_delete = []
    for db_pool_id, fuzzing_pool_id, fuzzing_platform in Pool.objects.values_list('id', 'pool_id', 'platform'):
        if (fuzzing_platform, fuzzing_pool_id) not in pools_seen:
            to_delete.append(db_pool_id)
    while to_delete:
        delete_now, to_delete = to_delete[:500], to_delete[500:]
        LOG.warning("deleting pools: %r", delete_now)
        Pool.objects.filter(id__in=delete_now).delete()
