from __future__ import annotations

import functools
from django.conf import settings
from fasteners import InterProcessLock
import os
import sys
from types import TracebackType
from typing import Any
from typing import Callable
from typing import Literal
from typing import Type
from typing import TypeVar

LOCK_PATH = os.path.realpath(os.path.join(settings.BASE_DIR, 'mgmt'))
RetType = TypeVar("RetType")

class ManagementLock(object):

    def __init__(self) -> None:
        self.lock: InterProcessLock = None

    def acquire(self) -> None:
        self.lock = InterProcessLock(LOCK_PATH)

        # Attempt to obtain a lock, retry every 10 seconds. Wait at most 5 minutes.
        # The retrying is necessary so we can report on stderr that we are waiting
        # for a lock. Otherwise, a user trying to run the command manually might
        # get confused why the command execution is delayed.
        if self.lock.acquire(blocking=False):
            return
        print("Another management command is running, waiting for lock...", file=sys.stderr)
        if self.lock.acquire(delay=10, max_delay=10, timeout=300):
            return

        self.lock = None
        raise RuntimeError("Failed to acquire lock.")

    def release(self) -> None:
        if self.lock is not None:
            self.lock.release()

    def __enter__(self) -> ManagementLock:
        self.acquire()
        return self

    def __exit__(
            self,
            _exc_type: Type[BaseException] | None,
            _exc_val: BaseException | None,
            _exc_tb: TracebackType | None,
        ) -> Literal[False]:
        self.release()
        return False


def mgmt_lock_required(method: Callable[..., RetType]) -> Callable[..., RetType]:
    """
    Decorator to use on management methods that shouldn't run in parallel
    """
    @functools.wraps(method)
    def decorator(*args: Any, **options: Any) -> RetType:
        with ManagementLock():
            return method(*args, **options)
    return decorator
