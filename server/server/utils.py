import logging
import time
import uuid
import redis


LOG = logging.getLogger("fuzzmanager.utils")


class RedisLock(object):
    """Simple Redis mutex lock.

    based on: https://redislabs.com/ebook/part-2-core-concepts/chapter-6-application-components-in-redis \
                                   /6-2-distributed-locking/6-2-3-building-a-lock-in-redis/

    Not using RedLock because it isn't passable as a celery argument, so we can't release the lock in an async chain.
    """

    def __init__(self, conn, name, unique_id=None):
        self.conn = conn
        self.name = name
        if unique_id is None:
            self.unique_id = str(uuid.uuid4())
        else:
            self.unique_id = unique_id

    def acquire(self, acquire_timeout=10, lock_expiry=None):
        end = time.time() + acquire_timeout
        while time.time() < end:
            if self.conn.set(self.name, self.unique_id, ex=lock_expiry, nx=True):
                LOG.debug("Acquired lock: %s(%s)", self.name, self.unique_id)
                return self.unique_id

            time.sleep(0.05)

        LOG.debug("Failed to acquire lock: %s(%s)", self.name, self.unique_id)
        return None

    def release(self):
        with self.conn.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(self.name)
                    existing = pipe.get(self.name)
                    if not isinstance(existing, str):
                        existing = existing.decode("ascii")

                    if existing == self.unique_id:
                        pipe.multi()
                        pipe.delete(self.name)
                        pipe.execute()
                        LOG.debug("Released lock: %s(%s)", self.name, self.unique_id)
                        return True

                    pipe.unwatch()
                    break

                except redis.exceptions.WatchError:
                    pass

        LOG.debug("Failed to release lock: %s(%s) != %s", self.name, self.unique_id, existing)
        return False
