import sys
from contextlib import suppress
from logging import getLogger
from time import sleep, time
from uuid import uuid4

from redis.exceptions import WatchError

if sys.version_info[:2] < (3, 12):
    from collections.abc import Iterable, Iterator
    from itertools import islice
    from typing import TypeVar

LOG = getLogger("webcompatmanager.utils")


class RedisLock:
    """Simple Redis mutex lock.

    based on: https://redislabs.com/ebook/part-2-core-concepts \
              /chapter-6-application-components-in-redis/6-2-distributed-locking \
              /6-2-3-building-a-lock-in-redis/

    Not using RedLock because it isn't passable as a celery argument, so we can't
    release the lock in an async chain.
    """

    def __init__(self, conn, name, unique_id=None):
        self.conn = conn
        self.name = name
        if unique_id is None:
            self.unique_id = str(uuid4())
        else:
            self.unique_id = unique_id

    def acquire(self, acquire_timeout=10, lock_expiry=None):
        end = time() + acquire_timeout
        while time() < end:
            if self.conn.set(self.name, self.unique_id, ex=lock_expiry, nx=True):
                LOG.debug("Acquired lock: %s(%s)", self.name, self.unique_id)
                return self.unique_id

            sleep(0.05)

        LOG.debug("Failed to acquire lock: %s(%s)", self.name, self.unique_id)
        return None

    def release(self):
        with self.conn.pipeline() as pipe:
            while True:
                with suppress(WatchError):
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

        LOG.debug(
            "Failed to release lock: %s(%s) != %s", self.name, self.unique_id, existing
        )
        return False


if sys.version_info[:2] < (3, 12):
    # generic type for `batched` below
    _T = TypeVar("_T")

    # added to itertools in 3.12
    def batched(iterable: Iterable[_T], n: int) -> Iterator[tuple[_T, ...]]:
        # batched('ABCDEFG', 3) → ABC DEF G
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(islice(iterator, n)):
            yield batch
