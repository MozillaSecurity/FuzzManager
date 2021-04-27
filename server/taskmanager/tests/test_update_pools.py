# coding: utf-8
'''Tests for TaskManager tasks

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import datetime
import logging
import os.path
import pytest
import sys
from dateutil.parser import isoparse
# from taskmanager.cron import delete_expired
from taskmanager.tasks import update_task, update_pool_defns
from taskmanager.models import Pool, Task


LOG = logging.getLogger('fm.taskmanager.tests.tasks')
pytestmark = [  # pylint: disable=invalid-name
    pytest.mark.skipif(sys.version_info < (3, 6), reason="fuzzing-tc requires python3.6 or higher"),
    pytest.mark.usefixtures("taskmanager_test"),
]


TASK_EVENT_DATA = {
    "task-completed": [
        {
            "status": {
                "taskId": "Z1kaoRtHRRWyyuMDqadYPA",
                "provisionerId": "proj-fuzzing",
                "workerType": "linux-pool10",
                "taskQueueId": "proj-fuzzing/linux-pool10",
                "schedulerId": "-",
                "projectId": "none",
                "taskGroupId": "P_zY5AHsRxGBemA-bU1A2A",
                "deadline": "2021-04-20T03:41:59.959Z",
                "expires": "2021-04-27T00:41:59.959Z",
                "retriesLeft": 5, "state": "completed",
                "runs": [
                    {
                        "runId": 0,
                        "state": "completed",
                        "reasonCreated": "scheduled",
                        "reasonResolved": "completed",
                        "workerGroup": "us-east1",
                        "workerId": "3226121097968852402",
                        "takenUntil": "2021-04-20T03:53:19.026Z",
                        "scheduled": "2021-04-20T00:42:01.902Z",
                        "started": "2021-04-20T00:43:17.169Z",
                        "resolved": "2021-04-20T03:37:35.398Z",
                    },
                ],
            },
            "runId": 0,
            "task": {"tags": {}},
            "workerGroup": "us-east1",
            "workerId": "3226121097968852402",
            "version": 1,
        },
        {
            "pool": {
                "platform": "linux",
                "pool_name": "pool10",
                "size": None,
                "cpu": None,
                "cycle_time": None,
                "max_run_time": None,
            },
            "task": {
                "task_id": "Z1kaoRtHRRWyyuMDqadYPA",
                "run_id": 0,
                "decision_id": "P_zY5AHsRxGBemA-bU1A2A",
                "expires": isoparse("2021-04-27T00:41:59.959Z"),
                "resolved": isoparse("2021-04-20T03:37:35.398Z"),
                "started": isoparse("2021-04-20T00:43:17.169Z"),
                "created": isoparse("1970-01-01T12:00:00Z"),
                "state": "completed",
            },
        },
    ],
    "task-exception": [
        {
            "status": {
                "taskId": "f8fRfedPSp2-A7M9Zhxe-Q",
                "provisionerId": "proj-fuzzing",
                "workerType": "linux-pool44",
                "taskQueueId": "proj-fuzzing/linux-pool44",
                "schedulerId": "-",
                "projectId": "none",
                "taskGroupId": "eW36sOvMTV6vM-XphAs07Q",
                "deadline": "2021-04-20T03:45:44.796Z",
                "expires": "2021-04-27T00:45:44.796Z",
                "retriesLeft": 5,
                "state": "exception",
                "runs": [
                    {
                        "runId": 0,
                        "state": "exception",
                        "reasonCreated": "scheduled",
                        "reasonResolved": "deadline-exceeded",
                        "workerGroup": "us-east4",
                        "workerId": "6898597828614134433",
                        "takenUntil": "2021-04-20T04:01:41.221Z",
                        "scheduled": "2021-04-20T01:01:39.323Z",
                        "started": "2021-04-20T01:01:39.703Z",
                        "resolved": "2021-04-20T03:46:46.569Z",
                    },
                ],
            },
            "runId": 0,
            "version": 1,
        },
        {
            "pool": {
                "platform": "linux",
                "pool_name": "pool44",
                "size": None,
                "cpu": None,
                "cycle_time": None,
                "max_run_time": None,
            },
            "task": {
                "task_id": "f8fRfedPSp2-A7M9Zhxe-Q",
                "run_id": 0,
                "decision_id": "eW36sOvMTV6vM-XphAs07Q",
                "expires": isoparse("2021-04-27T00:45:44.796Z"),
                "resolved": isoparse("2021-04-20T03:46:46.569Z"),
                "started": isoparse("2021-04-20T01:01:39.703Z"),
                "created": isoparse("1970-01-01T12:00:00Z"),
                "state": "exception",
            },
        },
    ],
    "task-pending": [
        {
            "status": {
                "taskId": "bQH-9tlpRXa8_qa9OVBBFw",
                "provisionerId": "proj-fuzzing",
                "workerType": "linux-pool7",
                "taskQueueId": "proj-fuzzing/linux-pool7",
                "schedulerId": "-",
                "projectId": "none",
                "taskGroupId": "bgcH8_hBTNeXwrMyFNHr9A",
                "deadline": "2021-04-20T09:30:38.640Z",
                "expires": "2021-04-27T03:30:38.640Z",
                "retriesLeft": 5,
                "state": "pending",
                "runs": [
                    {
                        "runId": 0,
                        "state": "pending",
                        "reasonCreated": "scheduled",
                        "scheduled": "2021-04-20T03:30:46.969Z",
                    },
                ],
            },
            "runId": 0,
            "version": 1,
        },
        {
            "pool": {
                "platform": "linux",
                "pool_name": "pool7",
                "size": None,
                "cpu": None,
                "cycle_time": None,
                "max_run_time": None,
            },
            "task": {
                "task_id": "bQH-9tlpRXa8_qa9OVBBFw",
                "run_id": 0,
                "decision_id": "bgcH8_hBTNeXwrMyFNHr9A",
                "expires": isoparse("2021-04-27T03:30:38.640Z"),
                "resolved": None,
                "started": None,
                "created": isoparse("1970-01-01T12:00:00Z"),
                "state": "pending",
            },
        },
    ],
    "task-running": [
        {
            "status": {
                "taskId": "bQH-9tlpRXa8_qa9OVBBFw",
                "provisionerId": "proj-fuzzing",
                "workerType": "linux-pool7",
                "taskQueueId": "proj-fuzzing/linux-pool7",
                "schedulerId": "-",
                "projectId": "none",
                "taskGroupId": "bgcH8_hBTNeXwrMyFNHr9A",
                "deadline": "2021-04-20T09:30:38.640Z",
                "expires": "2021-04-27T03:30:38.640Z",
                "retriesLeft": 5,
                "state": "running",
                "runs": [
                    {
                        "runId": 0,
                        "state": "running",
                        "reasonCreated": "scheduled",
                        "workerGroup": "us-east1",
                        "workerId": "5287870404102452225",
                        "takenUntil": "2021-04-20T03:52:24.713Z",
                        "scheduled": "2021-04-20T03:30:46.969Z",
                        "started": "2021-04-20T03:32:24.718Z",
                    },
                ],
            },
            "runId": 0,
            "workerGroup": "us-east1",
            "workerId": "5287870404102452225",
            "takenUntil": "2021-04-20T03:52:24.713+00:00",
            "version": 1,
        },
        {
            "pool": {
                "platform": "linux",
                "pool_name": "pool7",
                "size": None,
                "cpu": None,
                "cycle_time": None,
                "max_run_time": None,
            },
            "task": {
                "task_id": "bQH-9tlpRXa8_qa9OVBBFw",
                "run_id": 0,
                "decision_id": "bgcH8_hBTNeXwrMyFNHr9A",
                "expires": isoparse("2021-04-27T03:30:38.640Z"),
                "resolved": None,
                "started": isoparse("2021-04-20T03:32:24.718Z"),
                "created": isoparse("1970-01-01T12:00:00Z"),
                "state": "running",
            },
        },
    ],
}


@pytest.mark.parametrize("pulse_data, expected", TASK_EVENT_DATA.values())
def test_update_task_0(mocker, settings, pulse_data, expected):
    """test that Task events update the DB"""
    settings.TC_EXTRA_POOLS = ["extra"]
    settings.TC_ROOT_URL = "https://allizom.org/tc"

    mock_queue = mocker.patch("taskcluster.Queue")
    mock_queue.return_value.task.return_value = {"created": "1970-01-01T12:00:00Z"}

    update_task(pulse_data)

    assert mock_queue.call_count == 1
    assert mock_queue.return_value.task.call_count == 1

    assert Pool.objects.count() == 1
    assert Task.objects.count() == 1

    pool_obj = Pool.objects.get()
    for field, value in expected["pool"].items():
        assert getattr(pool_obj, field) == value
    task_obj = Task.objects.get()
    for field, value in expected["task"].items():
        assert getattr(task_obj, field) == value


def test_update_pool_defns_0(mocker, settings):
    """test that Pool definition is read from GH"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool1")
    settings.TC_FUZZING_CFG_REPO = "git@allizom.org:allizom/fuzzing-config.git"
    settings.TC_EXTRA_POOLS = ["extra"]

    mock_call = mocker.patch("taskmanager.tasks.check_output")

    update_pool_defns()

    assert mock_call.call_count == 4
    assert Pool.objects.count() == 1
    assert Task.objects.count() == 0

    pool = Pool.objects.get()
    assert pool.pool_id == "pool1"
    assert pool.pool_name == "Test Pool"
    assert pool.platform == "linux"
    assert pool.size == 2
    assert pool.cpu == "x64"
    assert pool.cycle_time == datetime.timedelta(hours=1)
    assert pool.max_run_time == datetime.timedelta(hours=1)


# existing pools with no tasks in GH are not deleted

# existing pools with tasks but not in GH are not deleted

# existing pool with no tasks and not in GH are deleted

# expired tasks are deleted
