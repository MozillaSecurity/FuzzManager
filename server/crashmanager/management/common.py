# Ensure print() compatibility with Python 3
from __future__ import print_function

from django.conf import settings
from lockfile import FileLock, LockTimeout
import os
import sys

LOCK_PATH = os.path.join(settings.BASE_DIR, 'mgmt')

class ManagementLock():
    def __init__(self):
        self.lock = None
        
    def aquire(self):
        self.lock = FileLock(LOCK_PATH)
        reported = False
        
        # Attempt to obtain a lock, retry every 10 seconds. Wait at most 10 minutes.
        # The retrying is necessary so we can report on stderr that we are waiting
        # for a lock. Otherwise, a user trying to run the command manually might
        # get confused why the command execution is delayed.
        for idx in range(0,30):  # @UnusedVariable
            try:
                self.lock.acquire(10)
                return
            except LockTimeout:
                if not reported:
                    print("Another management command is running, waiting for lock...", file=sys.stderr)
                    reported = True
        
        raise RuntimeError("Failed to aquire lock.")
    
    def release(self):
        if self.lock:
            self.lock.release()


def mgmt_lock_required(method):
    """
    Decorator to use on management methods that shouldn't run in parallel
    """
    def decorator(self, *args, **options):
        lock = ManagementLock()
        lock.aquire()
        try:
            method(self, *args, **options)
        finally:
            lock.release()
        return
    return decorator 