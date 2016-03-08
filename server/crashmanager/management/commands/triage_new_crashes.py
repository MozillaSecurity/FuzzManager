from django.core.management.base import NoArgsCommand

from crashmanager.management.common import mgmt_lock_required
from crashmanager.models import CrashEntry, Bucket


class Command(NoArgsCommand):
    help = "Iterates over all unbucketed crash entries that have never been triaged before to assign them into the existing buckets."
    @mgmt_lock_required
    def handle_noargs(self, **options):
        entries = CrashEntry.objects.filter(triagedOnce=False, bucket=None)
        buckets = Bucket.objects.all()

        for bucket in buckets:
            signature = bucket.getSignature()
            needTest = signature.matchRequiresTest()

            for entry in entries:
                if signature.matches(entry.getCrashInfo(attachTestcase=needTest)):
                    entry.bucket = bucket

                entry.triagedOnce = True
                entry.save()

        # This query ensures that all issues that have been bucketed manually before
        # the server had a chance to triage them will have their triageOnce flag set,
        # so the hourglass in the UI isn't displayed anymore.
        CrashEntry.objects.exclude(bucket=None).update(triagedOnce=True)
