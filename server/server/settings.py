"""
Django settings for server project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

FTB_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path += [FTB_PATH]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_FILE = "settings.secret"
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
    'crashmanager',
    'rest_framework',
    'rest_framework.authtoken',
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

# Crashmanager configuration
#
#BUGZILLA_USERNAME = "example@example.com"
#BUGZILLA_PASSWORD = "secret"
#CLEANUP_CRASHES_AFTER_DAYS = 14
#CLEANUP_FIXED_BUCKETS_AFTER_DAYS = 3

# This is the base directory where the tests/ subdirectory will
# be created for storing submitted test files.
TEST_STORAGE = os.path.join(BASE_DIR)
