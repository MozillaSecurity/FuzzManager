from .settings import *  # noqa

# Run in production mode
DEBUG = False

# This secret only exists to facilitate container testing.
# This is not used in production.
SECRET_KEY = "YskonP1FOlIthZKysJcXQ3Bn6sAjUXaei8JVjesWbE"

# Allow localhost
ALLOWED_HOSTS = ["localhost"]

BASE_DIR = "/data"
COV_STORAGE = "/data/coverage"
TEST_STORAGE = "/data/crashes"
USERDATA_STORAGE = "/data/userdata"
TC_ROOT_URL = ""
TC_PROJECT = ""
TC_EXTRA_POOLS = []

REDIS_URL = (
    "redis://fuzzmanager-redis:6379?db=0"  # unix sockets, use unix:///path/to/sock?db=0
)
CELERY_BROKER_URL = "redis://fuzzmanager-redis/2"
CELERY_RESULT_BACKEND = "redis://fuzzmanager-redis/1"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "fuzzmanager",
        "USER": "fuzzmanager",
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
