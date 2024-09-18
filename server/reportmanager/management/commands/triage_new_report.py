from collections import OrderedDict

from django.conf import settings
from django.core.management import BaseCommand

from reportmanager.models import Bucket, ReportEntry

# This is a per-worker global cache mapping short descriptions of
# reports to a list of bucket candidates to try first.
#
# although this cache looks pointless within this command,
# the command is called in a loop from triage_new_reports.py
# and may be called multiple times in one process by celery
TRIAGE_CACHE = OrderedDict()


class Command(BaseCommand):
    help = "Triage a report entry into an existing bucket."

    def add_arguments(self, parser):
        parser.add_argument(
            "id",
            type=int,
            help="Report ID",
        )

    def handle(self, *args, **options):
        entry = ReportEntry.objects.get(pk=options["id"])
        report_info = entry.get_report_info(attach_testcase=True)

        cache_hit = False

        triage_cache_hint = TRIAGE_CACHE.get(entry.short_signature, [])

        if triage_cache_hint:
            buckets = Bucket.objects.filter(pk__in=triage_cache_hint).order_by("-id")
            for bucket in buckets:
                signature = bucket.get_signature()
                if signature.matches(report_info):
                    entry.bucket = bucket
                    print("Cache hit")
                    cache_hit = True
                    break

        if not cache_hit:
            buckets = Bucket.objects.exclude(pk__in=triage_cache_hint).order_by("-id")

            for bucket in buckets:
                signature = bucket.get_signature()
                if signature.matches(report_info):
                    entry.bucket = bucket

                    cache_list = [bucket.pk]
                    if triage_cache_hint:
                        cache_list = TRIAGE_CACHE[entry.short_signature]

                        # We delete the current entry and add it again to ensure
                        # that our dictionary remains ordered by the time of last
                        # use. We can then just pop the first element if the cache
                        # grows too large, evicting the least used item.
                        del TRIAGE_CACHE[entry.short_signature]
                        cache_list.append(bucket.pk)

                    TRIAGE_CACHE[entry.short_signature] = cache_list

                    if len(TRIAGE_CACHE) > getattr(
                        settings, "CELERY_TRIAGE_MEMCACHE_ENTRIES", 100
                    ):
                        TRIAGE_CACHE.popitem(last=False)

                    break

        entry.triaged_once = True
        entry.save()
