import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings_nondebug")

app = Celery("tasks")
app.config_from_object("django.conf:settings", namespace="CELERY")
