from fakeredis import FakeConnection

from .settings import *  # noqa

TC_ROOT_URL = ""  # must be set for taskmanager tests
TC_PROJECT = ""  # must be set for taskmanager tests
USE_CELERY = False

# Override the cache settings to use fakeredis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379?db=0",
        "OPTIONS": {"connection_class": FakeConnection},
    }
}
