# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any

from django.core.management import BaseCommand  # noqa

from ...models import Pool


class Command(BaseCommand):
    help = "List Taskmanager pools"

    def handle(self, *args: Any, **options: Any) -> None:
        for pool in Pool.objects.all():
            if pool.pool_id != f"pool{pool.id}":
                print(f"!=: {pool.id} ({pool.pool_id})")
            else:
                print(f"ok: {pool.id} ({pool.pool_id})")
