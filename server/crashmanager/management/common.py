# Ensure print() compatibility with Python 3
from __future__ import print_function

import functools
from django.conf import settings
from fasteners import InterProcessLock
import os
import sys

LOCK_PATH = os.path.realpath(os.path.join(settings.BASE_DIR, 'mgmt'))


class ManagementLock(object):

    def __init__(self):
        self.lock = None

    def acquire(self):
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

    def release(self):
        if self.lock is not None:
            self.lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.release()
        return False


def mgmt_lock_required(method):
    """
    Decorator to use on management methods that shouldn't run in parallel
    """
    @functools.wraps(method)
    def decorator(*args, **options):
        with ManagementLock():
            return method(*args, **options)
    return decorator
