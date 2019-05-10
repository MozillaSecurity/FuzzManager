from __future__ import absolute_import

from celery import Celery
import os

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings_nondebug')

app = Celery('tasks')
app.config_from_object('django.conf:settings', namespace='CELERY')
