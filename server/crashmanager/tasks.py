import redis
from celeryconf import app
from django.conf import settings
from django.core.management import call_command

from . import cron  # noqa ensure cron tasks get registered


@app.task(ignore_result=True)
def async_reassign(pk, token):
    from .models import Bucket

    bucket = Bucket.objects.get(pk=pk)
    bucket.reassign(True)
    Bucket.objects.filter(pk=pk).update(reassign_in_progress=False)

    cache = redis.StrictRedis.from_url(settings.REDIS_URL)
    cache.srem("cm_async_operations", token)


@app.task(ignore_result=True, serializer="pickle")
def bulk_delete_crashes(query, token):
    from .models import CrashEntry

    queryset = CrashEntry.objects.all()
    queryset.query = query

    pks = list(queryset.values_list("id", flat=True))
    while pks:
        chunk, pks = pks[:100], pks[100:]
        CrashEntry.objects.filter(pk__in=chunk).delete()
    cache = redis.StrictRedis.from_url(settings.REDIS_URL)
    cache.srem("cm_async_operations", token)


@app.task(ignore_result=True)
def triage_new_crash(pk):
    call_command("triage_new_crash", pk)
