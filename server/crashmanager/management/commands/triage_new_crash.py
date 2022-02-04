from collections import OrderedDict

from django.conf import settings
from django.core.management import BaseCommand

from crashmanager.models import CrashEntry, Bucket


# This is a per-worker global cache mapping short descriptions of
# crashes to a list of bucket candidates to try first.
#
# although this cache looks pointless within this command,
# the command is called in a loop from triage_new_crashes.py
# and may be called multiple times in one process by celery
TRIAGE_CACHE = OrderedDict()


class Command(BaseCommand):
    help = ("Triage a crash entry into an existing bucket.")

    def add_arguments(self, parser):
        parser.add_argument(
            "id",
            type=int,
            help="Crash ID",
        )

    def handle(self, *args, **options):
        entry = CrashEntry.objects.get(pk=options["id"])
        crashInfo = entry.getCrashInfo(attachTestcase=True)

        cacheHit = False

        triage_cache_hint = TRIAGE_CACHE.get(entry.shortSignature, [])

        if triage_cache_hint:
            buckets = Bucket.objects.filter(pk__in=triage_cache_hint).order_by('-id')
            for bucket in buckets:
                signature = bucket.getSignature()
                if signature.matches(crashInfo):
                    entry.bucket = bucket
                    print("Cache hit")
                    cacheHit = True
                    break

        if not cacheHit:
            buckets = Bucket.objects.exclude(pk__in=triage_cache_hint).order_by('-id')

            for bucket in buckets:
                signature = bucket.getSignature()
                if signature.matches(crashInfo):
                    entry.bucket = bucket

                    cacheList = [bucket.pk]
                    if triage_cache_hint:
                        cacheList = TRIAGE_CACHE[entry.shortSignature]

                        # We delete the current entry and add it again to ensure
                        # that our dictionary remains ordered by the time of last
                        # use. We can then just pop the first element if the cache
                        # grows too large, evicting the least used item.
                        del TRIAGE_CACHE[entry.shortSignature]
                        cacheList.append(bucket.pk)

                    TRIAGE_CACHE[entry.shortSignature] = cacheList

                    if len(TRIAGE_CACHE) > getattr(settings, 'CELERY_TRIAGE_MEMCACHE_ENTRIES', 100):
                        TRIAGE_CACHE.popitem(last=False)

                    break

        entry.triagedOnce = True
        entry.save()
