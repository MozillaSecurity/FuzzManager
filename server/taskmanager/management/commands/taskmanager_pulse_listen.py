from logging import getLogger
from pathlib import Path

from amqp.exceptions import PreconditionFailed
from django.conf import settings
from django.core.management import BaseCommand, CommandError  # noqa
from kombu import Connection, Exchange, Queue, binding
from kombu.mixins import ConsumerMixin

from ...tasks import update_pool_defns, update_task

LOG = getLogger("taskmanager.management.commands.listen")
REPO_SLUG = Path(settings.TC_FUZZING_CFG_REPO.split(":", 1)[1])


class TaskClusterConsumer(ConsumerMixin):
    queue = Queue(
        bindings=[
            binding(
                Exchange("exchange/taskcluster-queue/v1/task-pending", type="topic"),
                routing_key=f"primary.#.proj-{settings.TC_PROJECT}.#",
            ),
            binding(
                Exchange("exchange/taskcluster-queue/v1/task-running", type="topic"),
                routing_key=f"primary.#.proj-{settings.TC_PROJECT}.#",
            ),
            binding(
                Exchange("exchange/taskcluster-queue/v1/task-completed", type="topic"),
                routing_key=f"primary.#.proj-{settings.TC_PROJECT}.#",
            ),
            binding(
                Exchange("exchange/taskcluster-queue/v1/task-failed", type="topic"),
                routing_key=f"primary.#.proj-{settings.TC_PROJECT}.#",
            ),
            binding(
                Exchange("exchange/taskcluster-queue/v1/task-exception", type="topic"),
                routing_key=f"primary.#.proj-{settings.TC_PROJECT}.#",
            ),
            binding(
                Exchange("exchange/taskcluster-github/v1/push"),
                routing_key=f"primary.{REPO_SLUG.parent}.{REPO_SLUG.stem}",
            ),
        ],
        name=f"queue/{settings.TC_PULSE_USERNAME}/{Path(__file__).stem}",
    )

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(
            queues=self.queue, auto_declare=False, callbacks=[self.on_message]
        )
        queue = consumer.queues[0]
        try:
            queue.queue_declare()
        except PreconditionFailed as exc:
            LOG.warning(
                "failed to declare queue, trying to delete first (error: %s)", exc
            )
            queue.delete()
            queue.queue_declare()
        for bing in consumer.queues[0].bindings:
            bing.exchange(channel).declare(passive=True)
            queue.bind_to(exchange=bing.exchange, routing_key=bing.routing_key)
        return [consumer]

    def on_consume_ready(self, connection, channel, consumers, **kwargs):
        LOG.info("pulse listener starting")

    def on_message(self, body, message):
        if message.delivery_info["exchange"].startswith(
            "exchange/taskcluster-queue/v1/task-"
        ):
            LOG.info(
                "%s on %s for %s",
                message.delivery_info["routing_key"],
                message.delivery_info["exchange"],
                body["status"]["taskId"],
            )
            if body["status"]["schedulerId"] == "audit":
                LOG.debug(
                    "ignoring task %s update for schedulerId %s",
                    body["status"]["taskId"],
                    body["status"]["schedulerId"],
                )
            else:
                update_task.delay(body)
            message.ack()
            return
        if message.delivery_info["exchange"] == "exchange/taskcluster-github/v1/push":
            LOG.info(
                "%s on %s for %s",
                message.delivery_info["routing_key"],
                message.delivery_info["exchange"],
                body["body"]["ref"],
            )
            if body["body"]["ref"] == "refs/heads/master":
                update_pool_defns.delay()
            message.ack()
            return
        raise RuntimeError(
            f"Unhandled message: {message.delivery_info['routing_key']}"
            f" on {message.delivery_info['exchange']}"
        )


class Command(BaseCommand):
    help = (
        "Listens for Mozilla Pulse messages relating to TaskManager tasks, "
        "and schedule celery tasks to handle them"
    )

    def handle(self, *args, **options):
        try:
            with Connection(
                f"amqp://{settings.TC_PULSE_USERNAME}:{settings.TC_PULSE_PASSWORD}"
                f"@pulse.mozilla.org:5671/{settings.TC_PULSE_VHOST}?ssl=1"
            ) as connection:
                worker = TaskClusterConsumer(connection)
                worker.run()
        except Exception:
            LOG.exception("pulse listener raised")
            raise
        finally:
            LOG.warning("pulse listener stopped")
