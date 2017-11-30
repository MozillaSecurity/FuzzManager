#!/bin/sh -ex

celery -A celeryconf -l debug beat &
celery -A celeryconf -l info -c 4 -n cron@%h -Q cron worker &
celery -A celeryconf -l info -n worker@%h -Q celery worker
