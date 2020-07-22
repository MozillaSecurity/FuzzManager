# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging
import re

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from server.auth import CheckAppPermission
from server.views import JsonQueryFilterBackend, SimpleQueryFilterBackend, deny_restricted_users
from .models import Pool, Task
from .serializers import PoolSerializer, TaskSerializer

LOG = logging.getLogger("fm.taskmanager.views")

# If status is reported for an unknown task, we store it in the DB with the Pool key nulled.
# We can't show this in taskmanager until we know what pool it belongs to. If for some reason
# the task is never claimed by a pool, we set an expiry so it will be deleted.
UNKNOWN_TASK_STATUS_EXPIRES = datetime.timedelta(hours=1)


@deny_restricted_users
def index(request):
    return redirect('taskmanager:pool-list-ui')


@deny_restricted_users
def list_pools(request):
    return render(request, 'pool/index.html', {})


@deny_restricted_users
def view_pool(request, pk):
    pool = get_object_or_404(Pool, pk=pk)
    return render(request, 'pool/view.html', {"pool": pool, "tc_root_url": settings.TC_ROOT_URL})


class PoolViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows viewing Pools
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (CheckAppPermission,)
    queryset = Pool.objects.all()
    serializer_class = PoolSerializer
    paginate_by_param = 'limit'
    filter_backends = [
        JsonQueryFilterBackend,
        SimpleQueryFilterBackend,
    ]


class TaskViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """
    API endpoint that allows viewing Tasks
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (CheckAppPermission,)
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    paginate_by_param = 'limit'
    filter_backends = [
        JsonQueryFilterBackend,
        SimpleQueryFilterBackend,
    ]

    @action(detail=False, methods=['post'], authentication_classes=(TokenAuthentication,))
    def update_status(self, request):
        if set(request.data.keys()) != {"client", "status_data"}:
            LOG.debug("request.data.keys(): %s", request.data.keys())
            errors = {}
            if "client" not in request.data:
                errors["client"] = ["This field is required."]
            if "status_data" not in request.data:
                errors["status_data"] = ["This field is required."]
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        match = re.match(r"^task-(.+)-run-(\d+)$", request.data["client"])
        if match is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        now = datetime.datetime.now(timezone.utc)
        task, created = Task.objects.get_or_create(
            task_id=match.group(1),
            run_id=int(match.group(2)),
            defaults={
                "expires": now + UNKNOWN_TASK_STATUS_EXPIRES,
            },
        )

        serializer = TaskSerializer(
            task,
            data={"status_data": request.data["status_data"]},
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK)
        LOG.debug("TaskSerializer returned errors: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
