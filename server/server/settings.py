"""
Django settings for server project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: BASE_DIR / ...
from pathlib import Path

from django.conf import global_settings  # noqa

BASE_DIR = Path(__file__).parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_FILE = BASE_DIR / "settings.secret"
try:
    SECRET_KEY = SECRET_FILE.read_text().strip()
except OSError:
    try:
        with SECRET_FILE.open("w", encoding="ascii") as f:
            import random

            chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
            SECRET_KEY = "".join(random.choice(chars) for i in range(64))
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
    "reportmanager",
    "rest_framework",
    "rest_framework.authtoken",
    # 'mozilla_django_oidc',
    "crispy_forms",
    "crispy_bootstrap3",
    "notifications",
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


# We add a custom context processor to make our application name
# and certain other variables available in all our templates
def resolver_context_processor(request):
    return {
        "app_name": request.resolver_match.app_name,
        "namespace": request.resolver_match.namespace,
        "url_name": request.resolver_match.url_name,
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
                "server.settings.resolver_context_processor",
            ],
            "debug": True,
        },
    },
]


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap3"
CRISPY_TEMPLATE_PACK = "bootstrap3"

# This is code for Mozilla's 2FA using OID. If you have your own OID provider,
# you can probably use similar code to get 2FA for your WebCompatManager instance.

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
    r"/reportmanager/rest/.*",
)

# permissions given to new users by default
DEFAULT_PERMISSIONS = [
    "reportmanager.models.User:reportmanager_visible",
    "reportmanager.models.User:reportmanager_read",
]

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
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
STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "frontend/dist"]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("server.auth.CheckAppPermission",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
}

# Logging

LOG_DIR = BASE_DIR / "logs"
# If the logging directory does not exist, try creating it.
# If this happens to exist but is a file, we would die anyway
# once we try to create the log file, so don't bother checking
# this here.
LOG_DIR.mkdir(exist_ok=True, parents=True)

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
    },
}

# Setup CSRF trusted origins explicitly as it's needed from Django 4
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# If you are running WebCompatManager behind a TLS loadbalancer,
# uncomment the next line to let Django know that it should
# behave as if we were using HTTPs.
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Reportmanager configuration
#
# WebCompatManager supports username/password authentication as well as API keys
# for authenticating to a Bugzilla instance. Omitting the username will cause
# the password to be used as an API key instead.
# BUGZILLA_USERNAME = "example@example.com"
# BUGZILLA_PASSWORD = "secret"
# CLEANUP_REPORTS_AFTER_DAYS = 14
# CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 3
ALLOW_EMAIL_EDITION = True

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
    "reportmanager.cron.*": {"queue": "cron"},
}
CELERY_BEAT_SCHEDULE = {
    # 'Poll Bugzilla every 15 minutes': {
    #     'task': 'reportmanager.cron.bug_update_status',
    #     'schedule': 15 * 60,
    # },
    "Update ReportEntry stats every minute": {
        "task": "reportmanager.cron.update_report_stats",
        "schedule": 60,
    },
    "Cleanup ReportEntry/Bucket objects every 30 minutes": {
        "task": "reportmanager.cron.cleanup_old_reportes",
        "schedule": 30 * 60,
    },
}

# Email
EMAIL_SUBJECT_PREFIX = "[WebCompatManager] "
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Notifications
DJANGO_NOTIFICATIONS_CONFIG = {"USE_JSONFIELD": True}
