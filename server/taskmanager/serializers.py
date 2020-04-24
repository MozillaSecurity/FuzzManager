# -*- coding: utf-8 -*-
from rest_framework import serializers
from .models import Pool, Task


class PoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pool
        fields = "__all__"

    def to_representation(self, instance):
        """Add dynamic fields"""
        ret = super(PoolSerializer, self).to_representation(instance)
        ret["cycle_time"] = int(instance.cycle_time.total_seconds())
        ret["running"] = Task.objects.filter(pool=instance, state="running").count()
        if ret["size"] == 0:
            ret["status"] = "disabled"
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
