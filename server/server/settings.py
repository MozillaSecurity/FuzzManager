"""
Django settings for server project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os, sys
from django.conf import global_settings
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

FTB_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path += [FTB_PATH]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_FILE = os.path.join(BASE_DIR, "settings.secret")
try:
    SECRET_KEY = open(SECRET_FILE).read().strip()
except:
    try:
        with open(SECRET_FILE, 'w') as f:
            import random
            chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
            SECRET_KEY = ''.join([random.choice(chars) for i in range(64)])
            f.write(SECRET_KEY)
    except IOError:
        raise Exception('Cannot open file "%s" for writing.' % SECRET_FILE) 

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ec2spotmanager',
    'crashmanager',
    'rest_framework',
    'rest_framework.authtoken',
    'chartjs',
)

# This tiny middleware module allows us to see exceptions on stderr
# when running a Django instance with runserver.py
class ExceptionLoggingMiddleware(object):
    def process_exception(self, request, exception):
        import traceback
        print traceback.format_exc()


MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'server.settings.ExceptionLoggingMiddleware',
)

# We add a custom context processor to make our application name
# and certain other variables available in all our templates
def resolver_context_processor(request):
    return {
        'app_name': request.resolver_match.app_name,
        'namespace': request.resolver_match.namespace,
        'url_name': request.resolver_match.url_name
    }
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + ( 'server.settings.resolver_context_processor', )

# For basic auth, uncomment the following lines and the line
# in MIDDLEWARE_CLASSES containing RemoteUserMiddleware.
# You still have to configure basic auth through your webserver.
#
#AUTHENTICATION_BACKENDS = (
#    'django.contrib.auth.backends.RemoteUserBackend',
#)

ROOT_URLCONF = 'server.urls'

WSGI_APPLICATION = 'server.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }

# For a production setup, we recommend to not use sqlite
# but instead a real database like MySQL or Postgres.
#    'default': {
#        'ENGINE': 'django.db.backends.mysql',
#        'OPTIONS': {
#            'read_default_file': '/path/to/my.cnf',
#        },
#    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}

# Logging

LOG_DIR = os.path.join(BASE_DIR, "logs")
# If the logging directory does not exist, try creating it.
# If this happens to exist but is a file, we would die anyway
# once we try to create the log file, so don't bother checking
# this here.
if not os.path.exists(LOG_DIR):
  os.makedirs(LOG_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] [%(levelname)s] [%(module)s] [%(process)d] ]%(thread)d]: %(message)s'
        },
        'simple': {
            'format': '[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s'
        },
    },
   'handlers': {
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'ec2spotmanager_logfile':{
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'ec2spotmanager.log'),
            'maxBytes': '16777216',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        }
    },
    'loggers': {
        'ec2spotmanager': {
            'handlers': ['ec2spotmanager_logfile'],
            'propagate': True,
            'level': 'INFO',
        },
    },
}

# If you are running FuzzManager behind a TLS loadbalancer,
# uncomment the next line to let Django know that it should
# behave as if we were using HTTPs.
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Crashmanager configuration
#
#BUGZILLA_USERNAME = "example@example.com"
#BUGZILLA_PASSWORD = "secret"
#CLEANUP_CRASHES_AFTER_DAYS = 14
#CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 3

# This is the base directory where the tests/ subdirectory will
# be created for storing submitted test files.
TEST_STORAGE = os.path.join(BASE_DIR)
USERDATA_STORAGE = os.path.join(BASE_DIR)

# Celery configuration
# USE_CELERY = True
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TRIAGE_MEMCACHE_ENTRIES = 100
