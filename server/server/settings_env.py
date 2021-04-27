import environ
import os
from .settings import *  # noqa

DEBUG = False

env = environ.Env(
    # We run in production mode by default
    DEBUG=(bool, False),

    ALLOWED_HOSTS=(list, []),
)

# Base settings
DEBUG = env('DEBUG')
SECRET_KEY = env('SECRET_KEY')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Required database
DATABASES = {
    # read os.environ['DATABASE_URL'] and raises ImproperlyConfigured exception if not found
    'default': env.db(),
}

# Logs and Data storage
DATA_DIR = env.path('DATA_DIR')
LOG_DIR = os.path.join(DATA_DIR, "logs")
TEST_STORAGE = os.path.join(DATA_DIR, "test")
USERDATA_STORAGE = os.path.join(DATA_DIR, "userdata")
SIGNATURE_STORAGE = os.path.join(DATA_DIR, "signature")
for path in (LOG_DIR, TEST_STORAGE, USERDATA_STORAGE, SIGNATURE_STORAGE):
    os.makedirs(path, exist_ok=True)

# Redis configuration
REDIS_URL = env('REDIS_URL', default=REDIS_URL)
