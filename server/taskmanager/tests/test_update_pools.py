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
from django.utils import timezone
from taskmanager.cron import update_pools
from taskmanager.models import Pool, Task


LOG = logging.getLogger('fm.taskmanager.tests.tasks')
pytestmark = [  # pylint: disable=invalid-name
    pytest.mark.skipif(sys.version_info < (3, 6), reason="fuzzing-tc requires python3.6 or higher"),
    pytest.mark.usefixtures("taskmanager_test"),
]


def test_update_lock(mocker):
    """test lock skips update"""
    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return None
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    update_pools()

    assert mock_hooks.call_count == 0
    assert mock_queue.call_count == 0
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 0
    assert mock_redis.return_value.set.call_count == 0
    assert mock_call.call_count == 0


def test_update_tc_pools_0(mocker, settings):
    """no tasks in taskcluster, no pools in github"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool0")
    settings.TC_PROJECT = "fuzzing"
    settings.TC_FUZZING_CFG_REPO = "https://allizom.org/"

    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return "lock-uuid"
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    def _mock_hooks_list(*args, **kwds):
        return {
            "hooks": [],
        }
    mock_hooks.return_value.listHooks = mocker.Mock(side_effect=_mock_hooks_list)

    update_pools()

    assert mock_hooks.call_count == 1
    assert mock_hooks.return_value.listHooks.call_count == 1
    assert mock_hooks.return_value.listLastFires.call_count == 0
    assert mock_queue.call_count == 1
    assert mock_queue.return_value.listTaskGroup.call_count == 0
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 0
    assert mock_redis.return_value.set.call_count == 0
    assert mock_call.call_count == 4

    assert Pool.objects.count() == 0
    assert Task.objects.count() == 0


def test_update_tc_pools_1(mocker, settings):
    """test tasks found in TC, pools found in GH, orphan status adopted"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool1")
    settings.TC_PROJECT = "fuzzing"
    settings.TC_FUZZING_CFG_REPO = "https://allizom.org/"

    now = datetime.datetime.now(timezone.utc)

    og_task = Task.objects.create(
        task_id="abcd1234",
        run_id=0,
        status_data="Hello world",
        expires=now + datetime.timedelta(days=1),
    )
    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return "lock-uuid"
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    def _mock_hooks_list(*args, **kwds):
        return {
            "hooks": [{"hookId": "linux-pool1"}],
        }
    mock_hooks.return_value.listHooks = mocker.Mock(side_effect=_mock_hooks_list)

    def _mock_hooks_fires(*args, **kwds):
        return {
            "lastFires": [
                {
                    "result": "success",
                    "taskId": "decision123",
                },
            ],
        }
    mock_hooks.return_value.listLastFires = mocker.Mock(side_effect=_mock_hooks_fires)

    def _mock_queue_task_group(*args, **kwds):
        return {
            "tasks": [
                {
                    "status": {
                        "taskId": "abcd1234",
                        "runs": [
                            {
                                "runId": 0,
                                "state": "pending",
                            }
                        ],
                    },
                    "task": {
                        "created": now.isoformat(),
                        "expires": (now + datetime.timedelta(days=1)).isoformat(),
                    },
                },
                {
                    "status": {
                        "taskId": "wxyz7890",
                        "runs": [
                            {
                                "runId": 0,
                                "state": "pending",
                            }
                        ],
                    },
                    "task": {
                        "created": now.isoformat(),
                        "expires": (now + datetime.timedelta(days=1)).isoformat(),
                    },
                },
            ],
        }
    mock_queue.return_value.listTaskGroup = mocker.Mock(side_effect=_mock_queue_task_group)

    mock_redis.return_value.get.return_value = None

    update_pools()

    assert mock_hooks.call_count == 1
    assert mock_hooks.return_value.listHooks.call_count == 1
    assert mock_hooks.return_value.listLastFires.call_count == 1
    assert mock_queue.call_count == 1
    assert mock_queue.return_value.listTaskGroup.call_count == 1
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 1
    assert mock_redis.return_value.set.call_count == 0
    assert mock_call.call_count == 4

    pool = Pool.objects.get()
    assert pool.pool_name == "Test Pool"
    assert pool.platform == "linux"
    assert pool.size == 2
    assert pool.cpu == "x64"
    assert isinstance(pool.cycle_time, datetime.timedelta)
    assert isinstance(pool.max_run_time, datetime.timedelta)
    assert Task.objects.count() == 2
    for task in Task.objects.all():
        assert task.pool == pool
        assert task.task_id in {"abcd1234", "wxyz7890"}
        if task.task_id == "abcd1234":
            assert task.status_data == "Hello world"
            assert task.id == og_task.id
        else:
            assert task.status_data == ""
        assert task.run_id == 0
        assert isinstance(task.created, datetime.datetime)
        assert task.decision_id == "decision123"
        assert isinstance(task.expires, datetime.datetime)
        assert task.resolved is None
        assert task.started is None
        assert task.state == "pending"


def test_update_tc_pools_2(mocker, settings):
    """test tasks found in taskcluster, no pools found in github"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool2")
    settings.TC_PROJECT = "fuzzing"
    settings.TC_FUZZING_CFG_REPO = "https://allizom.org/"

    now = datetime.datetime.now(timezone.utc)

    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return "lock-uuid"
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    def _mock_hooks_list(*args, **kwds):
        return {
            "hooks": [{"hookId": "linux-pool1"}],
        }
    mock_hooks.return_value.listHooks = mocker.Mock(side_effect=_mock_hooks_list)

    def _mock_hooks_fires(*args, **kwds):
        return {
            "lastFires": [
                {
                    "result": "success",
                    "taskId": "decision123",
                },
            ],
        }
    mock_hooks.return_value.listLastFires = mocker.Mock(side_effect=_mock_hooks_fires)

    def _mock_queue_task_group(*args, **kwds):
        return {
            "tasks": [
                {
                    "status": {
                        "taskId": "abcd1234",
                        "runs": [
                            {
                                "runId": 0,
                                "state": "pending",
                            }
                        ],
                    },
                    "task": {
                        "created": now.isoformat(),
                        "expires": (now + datetime.timedelta(days=1)).isoformat(),
                    },
                },
            ],
        }
    mock_queue.return_value.listTaskGroup = mocker.Mock(side_effect=_mock_queue_task_group)

    mock_redis.return_value.get.return_value = None

    update_pools()

    assert mock_hooks.call_count == 1
    assert mock_hooks.return_value.listHooks.call_count == 1
    assert mock_hooks.return_value.listLastFires.call_count == 1
    assert mock_queue.call_count == 1
    assert mock_queue.return_value.listTaskGroup.call_count == 1
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 1
    assert mock_redis.return_value.set.call_count == 0
    assert mock_call.call_count == 4

    pool = Pool.objects.get()
    assert pool.pool_name == "linux-pool1"
    assert pool.platform == "linux"
    assert pool.size is None
    assert pool.cpu is None
    assert pool.cycle_time is None
    assert pool.max_run_time is None
    assert Task.objects.count() == 1
    for task in Task.objects.all():
        assert task.pool == pool
        assert task.task_id == "abcd1234"
        assert task.status_data == ""
        assert task.run_id == 0
        assert isinstance(task.created, datetime.datetime)
        assert task.decision_id == "decision123"
        assert isinstance(task.expires, datetime.datetime)
        assert task.resolved is None
        assert task.started is None
        assert task.state == "pending"


def test_update_tc_pools_3(mocker, settings):
    """test no tasks in taskcluster, pools in github"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool1")
    settings.TC_PROJECT = "fuzzing"
    settings.TC_FUZZING_CFG_REPO = "https://allizom.org/"

    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return "lock-uuid"
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    def _mock_hooks_list(*args, **kwds):
        return {
            "hooks": [],
        }
    mock_hooks.return_value.listHooks = mocker.Mock(side_effect=_mock_hooks_list)

    update_pools()

    assert mock_hooks.call_count == 1
    assert mock_hooks.return_value.listHooks.call_count == 1
    assert mock_hooks.return_value.listLastFires.call_count == 0
    assert mock_queue.call_count == 1
    assert mock_queue.return_value.listTaskGroup.call_count == 0
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 0
    assert mock_redis.return_value.set.call_count == 0
    assert mock_call.call_count == 4

    pool = Pool.objects.get()
    assert pool.pool_name == "Test Pool"
    assert pool.platform == "linux"
    assert pool.size == 2
    assert pool.cpu == "x64"
    assert isinstance(pool.cycle_time, datetime.timedelta)
    assert isinstance(pool.max_run_time, datetime.timedelta)
    assert Task.objects.count() == 0


def test_update_tc_pools_4(mocker, settings):
    """test all resolved get added to redis"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool1")
    settings.TC_PROJECT = "fuzzing"
    settings.TC_FUZZING_CFG_REPO = "https://allizom.org/"

    now = datetime.datetime.now(timezone.utc)

    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return "lock-uuid"
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    def _mock_hooks_list(*args, **kwds):
        return {
            "hooks": [{"hookId": "linux-pool1"}],
        }
    mock_hooks.return_value.listHooks = mocker.Mock(side_effect=_mock_hooks_list)

    def _mock_hooks_fires(*args, **kwds):
        return {
            "lastFires": [
                {
                    "result": "success",
                    "taskId": "decision123",
                },
            ],
        }
    mock_hooks.return_value.listLastFires = mocker.Mock(side_effect=_mock_hooks_fires)

    def _mock_queue_task_group(*args, **kwds):
        return {
            "tasks": [
                {
                    "status": {
                        "taskId": "abcd1234",
                        "runs": [
                            {
                                "runId": 0,
                                "state": "completed",
                                "started": (now - datetime.timedelta(days=2)).isoformat(),
                                "resolved": (now - datetime.timedelta(days=1)).isoformat(),
                            }
                        ],
                    },
                    "task": {
                        "created": (now - datetime.timedelta(days=2)).isoformat(),
                        "expires": (now + datetime.timedelta(days=1)).isoformat(),
                    },
                },
            ],
        }
    mock_queue.return_value.listTaskGroup = mocker.Mock(side_effect=_mock_queue_task_group)

    mock_redis.return_value.get.return_value = None

    def _mock_redis_set(key, value, **kwds):
        redis_mock_sets[key] = value
    redis_mock_sets = {}
    mock_redis.return_value.set = mocker.Mock(side_effect=_mock_redis_set)

    update_pools()

    assert mock_hooks.call_count == 1
    assert mock_hooks.return_value.listHooks.call_count == 1
    assert mock_hooks.return_value.listLastFires.call_count == 1
    assert mock_queue.call_count == 1
    assert mock_queue.return_value.listTaskGroup.call_count == 1
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 1
    assert mock_redis.return_value.set.call_count == 1
    assert mock_call.call_count == 4

    pool = Pool.objects.get()
    assert pool.pool_name == "Test Pool"
    assert pool.platform == "linux"
    assert pool.size == 2
    assert pool.cpu == "x64"
    assert isinstance(pool.cycle_time, datetime.timedelta)
    assert isinstance(pool.max_run_time, datetime.timedelta)
    assert Task.objects.count() == 1
    for task in Task.objects.all():
        assert task.pool == pool
        assert task.task_id == "abcd1234"
        assert task.status_data == ""
        assert task.run_id == 0
        assert isinstance(task.created, datetime.datetime)
        assert task.decision_id == "decision123"
        assert isinstance(task.expires, datetime.datetime)
        assert isinstance(task.resolved, datetime.datetime)
        assert isinstance(task.started, datetime.datetime)
        assert task.state == "completed"


def test_update_tc_pools_5(mocker, settings):
    """test resolved in redis get skipped in taskcluster"""
    settings.TC_FUZZING_CFG_STORAGE = os.path.join(os.path.dirname(__file__), "fixtures", "pool0")
    settings.TC_PROJECT = "fuzzing"
    settings.TC_FUZZING_CFG_REPO = "https://allizom.org/"

    mock_hooks = mocker.patch("taskcluster.Hooks")
    mock_queue = mocker.patch("taskcluster.Queue")
    mock_redis = mocker.patch("redis.StrictRedis.from_url")
    mock_lock = mocker.patch("taskmanager.cron.RedisLock")
    mock_call = mocker.patch("subprocess.check_output")

    def _mock_lock_acquire(*args, **kwds):
        return "lock-uuid"
    mock_lock.return_value.acquire = mocker.Mock(side_effect=_mock_lock_acquire)

    def _mock_hooks_list(*args, **kwds):
        return {
            "hooks": [{"hookId": "linux-pool1"}],
        }
    mock_hooks.return_value.listHooks = mocker.Mock(side_effect=_mock_hooks_list)

    def _mock_hooks_fires(*args, **kwds):
        return {
            "lastFires": [
                {
                    "result": "success",
                    "taskId": "decision123",
                },
            ],
        }
    mock_hooks.return_value.listLastFires = mocker.Mock(side_effect=_mock_hooks_fires)

    update_pools()

    assert mock_hooks.call_count == 1
    assert mock_hooks.return_value.listHooks.call_count == 1
    assert mock_hooks.return_value.listLastFires.call_count == 1
    assert mock_queue.call_count == 1
    assert mock_queue.return_value.listTaskGroup.call_count == 0
    assert mock_redis.call_count == 1
    assert mock_redis.return_value.get.call_count == 1
    assert mock_redis.return_value.set.call_count == 0
    assert mock_call.call_count == 4

    pool = Pool.objects.get()
    assert pool.pool_name == "linux-pool1"
    assert pool.platform == "linux"
    assert pool.size is None
    assert pool.cpu is None
    assert pool.cycle_time is None
    assert pool.max_run_time is None
    assert Task.objects.count() == 0
