from __future__ import annotations

import functools
from argparse import ArgumentParser
from collections.abc import Callable
from logging import getLogger
from typing import Any, Generator

import taskcluster
from django.conf import settings
from django.core.management import BaseCommand

from ...models import Task
from ...tasks import get_or_create_pool

LOG = getLogger("taskmanager.management.commands.scrape_group")


def paginated(func: Callable[..., Any], result_key: str) -> Callable[..., Any]:
    """Wraps a Taskcluster API that returns a result like:
    {
       continuationToken: "",
       result_key: [...]
    }
    This hides the process of re-requesting with continuationToken,
    and yields the contents of `result_key`
    """

    @functools.wraps(func)
    def _wrapped(*args: Any, **kwds: Any) -> Generator[Any, Any, Any]:
        kwds = kwds.copy()
        result = func(*args, **kwds)
        while result.get("continuationToken"):
            yield from result[result_key]
            kwds.setdefault("query", {})
            kwds["query"]["continuationToken"] = result["continuationToken"]
            result = func(*args, **kwds)
        yield from result[result_key]

    return _wrapped


class Command(BaseCommand):
    help = "Scrape a task group and add created tasks to taskmanager"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "task_group",
            help="Taskcluster task group to add tasks for",
        )
        parser.add_argument(
            "--no-decision",
            action="store_false",
            help="No decision task in group "
            "(ie. include task with taskId == taskGroupId)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        queue_svc = taskcluster.Queue({"rootUrl": settings.TC_ROOT_URL})
        task_group_id = options["task_group"]

        for task in paginated(queue_svc.listTaskGroup, "tasks")(task_group_id):
            # the task group id is for the decision
            # we only care about fuzzing tasks
            if options["no_decision"] and task["status"]["taskId"] == task_group_id:
                continue

            pool = get_or_create_pool(task["status"]["workerType"])
            if pool is None:
                LOG.debug(
                    "ignoring task %s update for workerType %s",
                    task["status"]["taskId"],
                    task["status"]["workerType"],
                )
                return None

            for run in task["status"]["runs"]:
                _, created = Task.objects.update_or_create(
                    task_id=task["status"]["taskId"],
                    run_id=run["runId"],
                    defaults={
                        "decision_id": task_group_id,
                        "created": task["task"]["created"],
                        "expires": task["task"]["expires"],
                        "resolved": run.get("resolved"),
                        "started": run.get("started"),
                        "state": run["state"],
                        "pool": pool,
                    },
                )
                LOG.info(
                    "%s task %s run %d in pool %s/%s -> %s",
                    "created" if created else "updated",
                    task["status"]["taskId"],
                    run["runId"],
                    pool.pool_id,
                    pool.platform,
                    run["state"],
                )
