# -*- coding: utf-8 -*-
import datetime
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from .models import Pool, Task


# For enabled pools, we calculate whether the run-time/cycle-time ratio
# is expected (compared to max_run_time). The threshold allows the ratio
# to be a bit lower than expected and still considered "healthy".
# The threshold is given as a ratio of cycle_time (eg. 0.03 is 3% of cycle-time).
RUN_RATIO_THRESHOLD = 0.03


class PoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pool
        fields = "__all__"

    def to_representation(self, instance):
        """Add dynamic fields"""
        ret = super(PoolSerializer, self).to_representation(instance)
        ret["cycle_time"] = None
        if instance.cycle_time is not None:
            ret["cycle_time"] = int(instance.cycle_time.total_seconds())
        ret["max_run_time"] = None
        if instance.max_run_time is not None:
            ret["max_run_time"] = int(instance.max_run_time.total_seconds())
        ret["running"] = Task.objects.filter(pool=instance, state="running").count()
        if ret["size"] == 0:
            ret["status"] = "disabled"
        elif ret["max_run_time"] is not None and ret["cycle_time"] is not None:
            # Get the run time for the last cycle period and check that it's expected.
            # New pools will show up as "partial" until a cycle_time has elapsed.
            duty_cycle = ret["max_run_time"] / ret["cycle_time"]
            now = datetime.datetime.now(timezone.utc)
            last_cycle_start = now - instance.cycle_time
            run_time = 0
            # We could exclude tasks that are not "success" or "running", but if errors
            # happen early, they will affect the ratio a lot, and if errors happen late,
            # fuzzing work probably happened and we should count it.
            query = (
                Q(pool=instance) &
                Q(started__isnull=False) &
                (Q(resolved__isnull=True) | Q(resolved__gte=last_cycle_start))
            )
            for task in Task.objects.filter(query):
                begin = max(task.started, last_cycle_start)
                end = task.resolved or now
                run_time += (end - begin).total_seconds()
            run_ratio = float(run_time) / ret["cycle_time"]
            # Only care if the run_ratio is less than duty_cycle by at least the
            # threshold.
            if (run_ratio - duty_cycle) >= -RUN_RATIO_THRESHOLD:
                ret["status"] = "healthy"
            elif run_time > 0:
                ret["status"] = "partial"
            else:
                ret["status"] = "idle"
        elif ret["running"] >= ret["size"]:
            ret["status"] = "healthy"
        elif ret["running"] > 0:
            ret["status"] = "partial"
        else:
            ret["status"] = "unknown"
        return ret


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        # all fields except "status_data"
        read_only_fields = (
            "pool_id", "task_id", "decision_id", "run_id", "state", "created",
            "started", "resolved", "expires",
        )
