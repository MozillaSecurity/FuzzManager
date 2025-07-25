"""
Django settings for server project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

from django.apps import apps
from django.conf import global_settings  # noqa

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_FILE = os.path.join(BASE_DIR, "settings.secret")
try:
    SECRET_KEY = open(SECRET_FILE).read().strip()
except OSError:
    try:
        with open(SECRET_FILE, "w") as f:
            import random

            chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
            SECRET_KEY = "".join([random.choice(chars) for i in range(64)])
            f.write(SECRET_KEY)
    except OSError:
        raise Exception(f'Cannot open file "{SECRET_FILE}" for writing.')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # 'livesync',
    "django.contrib.staticfiles",
    "ec2spotmanager",
    "crashmanager",
    "taskmanager",
    "covmanager",
    "rest_framework",
    "rest_framework.authtoken",
    "chartjs",
    # 'mozilla_django_oidc',
    "crispy_forms",
    "crispy_bootstrap3",
    "notifications",
    "server",
)


MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # 'django.contrib.auth.middleware.RemoteUserMiddleware',
    # 'mozilla_django_oidc.middleware.SessionRefresh',
    "server.middleware.RequireLoginMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "server.middleware.ExceptionLoggingMiddleware",
    "server.middleware.CheckAppPermissionsMiddleware",
    "server.middleware.AddXUsernameMiddleware",
    # 'livesync.core.middleware.DjangoLiveSyncMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
)


# We add a custom context processor to make installed_apps available in templates
def installed_apps_context_processor(_request):
    return {
        "installed_apps": tuple(app.name for app in apps.get_app_configs()),
    }


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                # Required in views imported from django-notifications
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "server.settings.installed_apps_context_processor",
            ],
            "debug": True,
        },
    },
]


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap3"
CRISPY_TEMPLATE_PACK = "bootstrap3"

# This is code for Mozilla's 2FA using OID. If you have your own OID provider,
# you can probably use similar code to get 2FA for your FuzzManager instance.

USE_OIDC = False

# Modify the way we generate our usernames, based on the email address
# OIDC_USERNAME_ALGO = 'server.auth.generate_username'
#
#
# OID_ALLOWED_USERS = {
#    "test@example.com",
# }

# For basic auth, uncomment the following lines and the line
# in MIDDLEWARE_CLASSES containing RemoteUserMiddleware.
# You still have to configure basic auth through your webserver.
#
# AUTHENTICATION_BACKENDS = (
#    'django.contrib.auth.backends.RemoteUserBackend',
#    'server.settings.FMOIDCAB',
# )


ROOT_URLCONF = "server.urls"

WSGI_APPLICATION = "server.wsgi.application"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "https://www.mozilla.org/"
LOGIN_REQUIRED_URLS_EXCEPTIONS = (
    r"/login/.*",
    r"/logout/.*",
    r"/oidc/.*",
    r"/ec2spotmanager/rest/.*",
    r"/covmanager/rest/.*",
    r"/taskmanager/rest/.*",
    r"/crashmanager/rest/.*",
)

# permissions given to new users by default
DEFAULT_PERMISSIONS = [
    "crashmanager.models.User:view_covmanager",
    "crashmanager.models.User:covmanager_all",
]

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
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

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "frontend/dist")]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("server.auth.CheckAppPermission",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"user": "100/minute"},
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
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "[%(asctime)s] [%(levelname)s] [%(module)s] [%(process)d] [%(thread)d]:"
                " %(message)s"
            ),
        },
        "simple": {"format": "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "ec2spotmanager_logfile": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "ec2spotmanager.log"),
            "maxBytes": 16777216,
            "formatter": "simple",
        },
        "taskmanager_logfile": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "taskmanager.log"),
            "maxBytes": 16777216,
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        "flake8": {
            "level": "WARNING",
        },
        "boto": {
            "handlers": ["ec2spotmanager_logfile"],
            "propagate": True,
            "level": "WARNING",
        },
        "laniakea": {
            "handlers": ["ec2spotmanager_logfile"],
            "propagate": True,
            "level": "INFO",
        },
        "libcloud": {
            "handlers": ["ec2spotmanager_logfile"],
            "propagate": True,
            "level": "INFO",
        },
        "ec2spotmanager": {
            "handlers": ["ec2spotmanager_logfile"],
            "propagate": True,
            "level": "INFO",
        },
        "taskmanager": {
            "handlers": ["taskmanager_logfile"],
            "propagate": True,
            "level": "INFO",
        },
    },
}

# Setup CSRF trusted origins explicitly as it's needed from Django 4
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# If you are running FuzzManager behind a TLS loadbalancer,
# uncomment the next line to let Django know that it should
# behave as if we were using HTTPs.
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# EC2Spotmanager configuration
# If access keys are None, boto will look for global credentials
# (~/.aws/credentials or IAM role)
#
AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None

# Google Compute credentials
# This is using service account credentials
# TODO: It should also be possible to use "installed application" or GCE role to
# authenticate, see libcloud docs
#
GCE_CLIENT_EMAIL = None  # these 3 fields are extracted from the JSON auth file
GCE_PROJECT_ID = None
GCE_PRIVATE_KEY = None  # PK as a string blob
GCE_API_KEY = (
    None  # this is a separate key created at "APIs & Services" / "Credentials"
)
GCE_AUTH_CACHE = "/tmp/.google_libcloud_auth.fuzzmanager-cluster"

# TaskManager configuration
#
# TaskManager is used to allow tracking fuzzing tasks run in a Taskcluster instance.
# Most people will find EC2 easier to use for small clusters.
#
# TC_FUZZING_CFG_REPO = ""  # URL to git repo containing Fuzzing pool configuration
# TC_FUZZING_CFG_STORAGE = BASE_DIR  # where to store the repo
# TC_ROOT_URL = ""  # root URL to the taskcluster instance
# TC_PROJECT = ""  # taskcluster project for fuzzing resources
# extra pools to include in TaskManager that don't fit the "platform-pool[0-9]+" pattern
# TC_EXTRA_POOLS = []

# Credentials for Mozilla Pulse instance used for by Taskcluster instance
# (for TaskManager)
# TC_PULSE_VHOST = ""
# TC_PULSE_USERNAME = ""
# TC_PULSE_PASSWORD = ""

# Crashmanager configuration
#
# FuzzManager supports username/password authentication as well as API keys
# for authenticating to a Bugzilla instance. Omitting the username will cause
# the password to be used as an API key instead.
# BUGZILLA_USERNAME = "example@example.com"
# BUGZILLA_PASSWORD = "secret"
# CLEANUP_CRASHES_AFTER_DAYS = 14
# CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 3
ALLOW_EMAIL_EDITION = True

# This is the base directory where the tests/ subdirectory will
# be created for storing submitted test files.
TEST_STORAGE = os.path.join(BASE_DIR)
USERDATA_STORAGE = os.path.join(BASE_DIR)

# This is the directory where signatures.zip will be stored
SIGNATURE_STORAGE = os.path.join(BASE_DIR)

# Redis configuration
REDIS_URL = "redis://localhost:6379?db=0"  # unix sockets, use unix:///path/to/sock?db=0

# Celery configuration
USE_CELERY = True
CELERY_ACCEPT_CONTENT = ["json", "pickle"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# For CELERY_BROKER_URL unix sockets, use redis+socket:///path/to/socket?virtual_host=0
CELERY_BROKER_URL = "redis:///2"
CELERY_RESULT_BACKEND = "redis:///1"
CELERY_TRIAGE_MEMCACHE_ENTRIES = 100
CELERY_TASK_ROUTES = {
    "covmanager.cron.*": {"queue": "cron"},
    "crashmanager.cron.*": {"queue": "cron"},
    "ec2spotmanager.cron.*": {"queue": "cron"},
    "taskmanager.cron.*": {"queue": "cron"},
}
CELERY_BEAT_SCHEDULE = {
    # 'Poll Bugzilla every 15 minutes': {
    #     'task': 'crashmanager.cron.bug_update_status',
    #     'schedule': 15 * 60,
    # },
    "Update CrashEntry stats every minute": {
        "task": "crashmanager.cron.update_crash_stats",
        "schedule": 60,
    },
    "Check for untriaged Crashes every 10 minutes": {
        "task": "crashmanager.cron.triage_new_crashes",
        "schedule": 10 * 60,
    },
    "Cleanup CrashEntry/Bucket objects every 30 minutes": {
        "task": "crashmanager.cron.cleanup_old_crashes",
        "schedule": 30 * 60,
    },
    "Create signatures.zip hourly": {
        "task": "crashmanager.cron.export_signatures",
        "schedule": 60 * 60,
    },
    # 'Update EC2SpotManager statistics': {
    #     'task': 'ec2spotmanager.cron.update_stats',
    #     'schedule': 60,
    # },
    # 'Check EC2SpotManager pools': {
    #     'task': 'ec2spotmanager.cron.check_instance_pools',
    #     'schedule': 60,
    # },
    # 'Cache EC2 spot market pricing in Redis': {
    #     'task': 'ec2spotmanager.cron.update_prices',
    #     'schedule': 15 * 60,
    # },
    # 'Poll TaskManager tasks with missed pulses': {
    #     'task': 'taskmanager.cron.update_tasks',
    #     'schedule': 15 * 60,
    # },
    "Cleanup expired TaskManager tasks": {
        "task": "taskmanager.cron.delete_expired",
        "schedule": 5 * 60,
    },
}

# Email
EMAIL_SUBJECT_PREFIX = "[FuzzManager] "
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Notifications
DJANGO_NOTIFICATIONS_CONFIG = {"USE_JSONFIELD": True}

# Report coverage reports with a drop of greater than 10%
COVERAGE_REPORT_DELTA = 10

# Setup cache settings
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
