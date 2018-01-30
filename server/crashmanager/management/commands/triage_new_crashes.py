from django.core.management import BaseCommand, CommandError  # noqa

from crashmanager.management.common import mgmt_lock_required
from crashmanager.models import CrashEntry, Bucket


class Command(BaseCommand):
    help = ("Iterates over all unbucketed crash entries that have never been triaged before to assign them "
            "into the existing buckets.")

    @mgmt_lock_required
    def handle(self, *args, **options):
        entries = CrashEntry.objects.filter(triagedOnce=False, bucket=None)
        buckets = Bucket.objects.all()

        signatureCache = {}

        for entry in entries:
            # Benchmarks have shown that always attaching the testcase
            # is faster than recreating the crash info in every iteration
            # when signatures can be cached.
            crashInfo = entry.getCrashInfo(attachTestcase=True)

            for bucket in buckets:
                if bucket.pk not in signatureCache:
                    signatureCache[bucket.pk] = bucket.getSignature()

                signature = signatureCache[bucket.pk]
                matched = False

                if signature.matches(crashInfo):
                    entry.bucket = bucket
                    matched = True

                entry.triagedOnce = True
                entry.save()

                if matched:
                    break

        # This query ensures that all issues that have been bucketed manually before
        # the server had a chance to triage them will have their triageOnce flag set,
        # so the hourglass in the UI isn't displayed anymore.
        CrashEntry.objects.exclude(bucket=None).update(triagedOnce=True)
