# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class Pool(models.Model):
    pool_id = models.CharField(max_length=255)  # filename in fuzzing-tc-config
    pool_name = models.CharField(max_length=255)  # friendly name
    platform = models.CharField(max_length=15)
    size = models.PositiveIntegerField(null=True)
    cpu = models.CharField(max_length=15, null=True)
    cycle_time = models.DurationField(null=True)
    max_run_time = models.DurationField(null=True)


class Task(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.deletion.CASCADE, null=True)
    task_id = models.CharField(max_length=64)
    decision_id = models.CharField(max_length=64, null=True)
    run_id = models.PositiveIntegerField()
    state = models.CharField(max_length=15)
    created = models.DateTimeField(null=True)
    status_data = models.CharField(max_length=4095, blank=True)
    started = models.DateTimeField(null=True)
    resolved = models.DateTimeField(null=True)
    expires = models.DateTimeField()

    class Meta:
        unique_together = (("task_id", "run_id"),)
