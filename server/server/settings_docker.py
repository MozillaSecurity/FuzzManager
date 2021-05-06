from .settings import *  # noqa

# Run in production mode
DEBUG = False

SECRET_KEY = "YskonP1FOlIthZKysJcXQ3Bn6sAjUXaei8JVjesWbE"

# Allow localhost
ALLOWED_HOSTS = ["localhost"]

BASE_DIR = "/data"
COV_STORAGE = "/data/coverage"
TEST_STORAGE = "/data/crashes"
USERDATA_STORAGE = "/data/userdata"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fuzzmanager',
        'USER': 'fuzzmanager',
        'PASSWORD': 'mozilla1234',
        'HOST': 'database',
    }
}
