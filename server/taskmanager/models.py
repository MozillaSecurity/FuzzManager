# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import cast

from django.db import models


class Pool(models.Model):
    pool_id = str(models.CharField(max_length=255))  # filename in fuzzing-tc-config
    pool_name = str(models.CharField(max_length=255))  # friendly name
    platform = str(models.CharField(max_length=15))
    size = int(str(models.PositiveIntegerField(null=True)))
    cpu = str(models.CharField(max_length=15, null=True))
    cycle_time = cast(timedelta, models.DurationField(null=True))
    max_run_time = cast(timedelta, models.DurationField(null=True))


class Task(models.Model):
    pool = cast(Pool, models.ForeignKey(Pool, on_delete=models.deletion.CASCADE, null=True))
    task_id = str(models.CharField(max_length=64))
    decision_id = str(models.CharField(max_length=64, null=True))
    run_id = int(str(models.PositiveIntegerField()))
    state = str(models.CharField(max_length=15))
    created = cast(datetime, models.DateTimeField(null=True))
    status_data = str(models.CharField(max_length=4095, blank=True))
    started = cast(datetime, models.DateTimeField(null=True))
    resolved = cast(datetime, models.DateTimeField(null=True))
    expires = cast(datetime, models.DateTimeField())

    class Meta:
        unique_together = (("task_id", "run_id"),)
