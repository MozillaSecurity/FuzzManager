from collections import OrderedDict

from django.conf import settings

from celeryconf import app
from . import cron  # noqa ensure cron tasks get registered

# This is a per-worker global cache mapping short descriptions of
# crashes to a list of bucket candidates to try first.
triage_cache = OrderedDict()


@app.task(ignore_result=True)
def triage_new_crash(pk):
    from .models import CrashEntry, Bucket
    entry = CrashEntry.objects.get(pk=pk)
    crashInfo = entry.getCrashInfo(attachTestcase=True)

    cacheHit = False

    triage_cache_hint = triage_cache.get(entry.shortSignature)

    if triage_cache_hint:
        buckets = Bucket.objects.filter(pk__in=triage_cache_hint)
        for bucket in buckets:
            signature = bucket.getSignature()
            if signature.matches(crashInfo):
                entry.bucket = bucket
                print("Cache hit")
                cacheHit = True
                break

    if not cacheHit:
        buckets = Bucket.objects.all()

        for bucket in buckets:
            signature = bucket.getSignature()
            if signature.matches(crashInfo):
                entry.bucket = bucket

                cacheList = [bucket.pk]
                if triage_cache_hint:
                    cacheList = triage_cache[entry.shortSignature]

                    # We delete the current entry and add it again to ensure
                    # that our dictionary remains ordered by the time of last
                    # use. We can then just pop the first element if the cache
                    # grows to large, evicting the least used item.
                    del triage_cache[entry.shortSignature]
                    cacheList.append(bucket.pk)

                triage_cache[entry.shortSignature] = cacheList

                # TODO: Make this length configurable
                if len(triage_cache) > getattr(settings, 'CELERY_TRIAGE_MEMCACHE_ENTRIES', 100):
                    triage_cache.popitem(last=False)

                break

    entry.triagedOnce = True
    entry.save()
