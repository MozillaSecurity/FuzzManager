# -*- coding: utf-8 -*-
from logging import getLogger
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError  # noqa
from mozillapulse.consumers import GenericConsumer, PulseConfiguration

from ...tasks import update_task, update_pool_defns


LOG = getLogger("taskmanager.management.commands.listen")


class TaskClusterConsumer(GenericConsumer):

    def __init__(self, **kwargs):
        repo_slug = Path(settings.TC_FUZZING_CFG_REPO.split(":", 1)[1])
        org = repo_slug.parent
        repo = repo_slug.stem
        exchanges = [
            "exchange/taskcluster-queue/v1/task-pending",
            "exchange/taskcluster-queue/v1/task-running",
            "exchange/taskcluster-queue/v1/task-completed",
            "exchange/taskcluster-queue/v1/task-failed",
            "exchange/taskcluster-queue/v1/task-exception",
            "exchange/taskcluster-github/v1/push",
        ]
        topics = ["primary.#.proj-%s.#" % settings.TC_PROJECT] * 5 + [
            "primary.%s.%s" % (org, repo),
        ]
        super().__init__(
            PulseConfiguration(**kwargs),
            exchanges,
            topic=topics,
            **kwargs,
        )
        for exchange, topic in zip(exchanges, topics):
            LOG.info("listening on %s for %s", exchange, topic)


class Command(BaseCommand):
    help = ("Listens for Mozilla Pulse messages relating to TaskManager tasks, "
            "and schedule celery tasks to handle them")

    def callback(self, body, msg):
        if msg.delivery_info["exchange"].startswith("exchange/taskcluster-queue/v1/task-"):
            LOG.info(
                "%s on %s for %s",
                msg.delivery_info["routing_key"],
                msg.delivery_info["exchange"],
                body["status"]["taskId"],
            )
            update_task.delay(body)
            msg.ack()
            return
        if msg.delivery_info["exchange"] == "exchange/taskcluster-github/v1/push":
            LOG.info(
                "%s on %s for %s",
                msg.delivery_info["routing_key"],
                msg.delivery_info["exchange"],
                body["body"]["ref"],
            )
            if body["body"]["ref"] == "refs/heads/master":
                update_pool_defns.delay()
            msg.ack()
            return
        raise RuntimeError(
            "Unhandled message: %s on %s" % (
                msg.delivery_info["routing_key"],
                msg.delivery_info["exchange"],
            )
        )

    def handle(self, *args, **options):
        LOG.info("pulse listener starting")
        try:
            TaskClusterConsumer(
                vhost=settings.TC_PULSE_VHOST,
                user=settings.TC_PULSE_USERNAME,
                password=settings.TC_PULSE_PASSWORD,
                callback=self.callback,
            ).listen()
        except Exception:
            LOG.exception()
            raise
        finally:
            LOG.warning("pulse listener stopped")
