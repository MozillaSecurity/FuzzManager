# -*- coding: utf-8 -*-
from logging import getLogger

from django.core.management import BaseCommand  # noqa

from ...models import Pool, Task


LOG = getLogger("taskmanager.management.commands.change_poolid")


class Command(BaseCommand):
    help = "Change a Taskmanager pool ID"

    def add_arguments(self, parser):
        parser.add_argument(
            "old",
            type=int,
            help="Original pool ID",
        )
        parser.add_argument(
            "new",
            type=int,
            help="Original pool ID",
        )

    def handle(self, *args, **options):
        old = options["old"]
        new = options["new"]

        assert not Pool.objects.filter(id=new).exists()
        pool = Pool.objects.get(id=old)
        pool.id = new
        pool.save()
        affected = Task.objects.filter(pool_id=old).update(pool_id=new)
        Pool.objects.get(id=old).delete()

        LOG.info("pool %d renamed to %d, affected %d tasks", old, new, affected)
        print(f"{affected} tasks moved")
