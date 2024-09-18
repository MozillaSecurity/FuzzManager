from pathlib import Path

from .settings import *  # noqa

# Run in production mode
DEBUG = False

# This secret only exists to facilitate container testing.
# This is not used in production.
SECRET_KEY = "YskonP1FOlIthZKysJcXQ3Bn6sAjUXaei8JVjesWbE"

# Allow localhost
ALLOWED_HOSTS = ["localhost"]

BASE_DIR = Path("/data")

# unix sockets, use unix:///path/to/sock?db=0
REDIS_URL = "redis://webcompatmanager-redis:6379?db=0"
CELERY_BROKER_URL = "redis://webcompatmanager-redis/2"
CELERY_RESULT_BACKEND = "redis://webcompatmanager-redis/1"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "webcompatmanager",
        "USER": "webcompatmanager",
        "PASSWORD": "mozilla1234",
        "HOST": "database",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
