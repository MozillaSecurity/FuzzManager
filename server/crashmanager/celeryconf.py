from __future__ import absolute_import

from celery import Celery
from django.conf import settings
import os

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings_nondebug')

app = Celery('tasks', broker='amqp://guest@localhost//')
app.config_from_object(settings)
