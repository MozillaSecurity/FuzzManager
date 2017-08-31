#!/bin/sh

celery -A celeryconf -l info worker
