# Ensure print() compatibility with Python 3
from __future__ import print_function

from django.conf import settings
import os
import errno

PIDFILE_BASEDIR = settings.BASE_DIR

class PIDLock():
    def __init__(self, filename):
        self.pidlock = None
        self.filename = filename
        
    def aquire(self):
        try:
            self.pidlock = os.open(self.filename, os.O_CREAT|os.O_WRONLY|os.O_EXCL)
        except OSError as e:
            if e.errno == errno.EEXIST:
                # TODO: Here we could check if the process still exists and is really running
                raise RuntimeError('Another process instance is already running')
            else:
                raise
                    
        os.write(self.pidlock, str(os.getpid()))
        os.close(self.pidlock)
    
    def release(self):
        if self.pidlock:
            os.remove(self.pidlock)


def pid_lock_file(method, fileprefix="default"):
    """
    Decorator to use on management methods that shouldn't run in parallel
    """
    def decorator(self, *args, **options):
        lock = PIDLock(os.path.join(PIDFILE_BASEDIR, fileprefix + ".pid"))
        lock.aquire()
        try:
            method(self, *args, **options)
        finally:
            lock.release()
        return
    return decorator 