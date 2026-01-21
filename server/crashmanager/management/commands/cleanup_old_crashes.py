import logging
from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand, CommandError  # noqa
from django.db.models.aggregates import Count
from django.utils import timezone

from crashmanager.models import Bucket, Bug, CrashEntry

LOG = logging.getLogger("fm.crashmanager.cleanup_old_crashes")


# Deleting things in buckets is complicated:
#
# Attempting to combine a subset (LIMIT) with a delete yields
#   "Cannot use 'limit' or 'offset' with delete."
#
# Using a nested query with pk_in=<filter query> yields
#   "This version of MySQL doesn't yet support
#        'LIMIT & IN/ALL/ANY/SOME subquery'"


# So the only way we have left is to manually select a given amount of
# pks and store them in a list to use pk__in with the list and a DELETE
# query.
def _bulk_delete_crashes(qs):
    while qs.count():
        pks = list(qs.values_list("pk", flat=True)[:500])
        CrashEntry.objects.filter(pk__in=pks).delete()


class Command(BaseCommand):
    help = "Cleanup old crash entries."

    def handle(self, *args, **options):
        cleanup_crashes_incl_buckets = getattr(settings, "CRASH_MAX_LIFETIME", 365 * 2)
        cleanup_crashes_after_days = getattr(settings, "CLEANUP_CRASHES_AFTER_DAYS", 14)
        cleanup_fixed_buckets_after_days = getattr(
            settings, "CLEANUP_FIXED_BUCKETS_AFTER_DAYS", 3
        )

        # start of day
        sod = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Select all very-old crashes, regardless of whether bucketed
        expiry_date = sod - timedelta(days=cleanup_crashes_incl_buckets)
        crashes = CrashEntry.objects.filter(created__lte=expiry_date)
        size = crashes.count()
        if size:
            LOG.info("Removing %d very old crashes", size)
        _bulk_delete_crashes(crashes)

        # Select all buckets that have been closed for x days
        expiry_date = sod - timedelta(days=cleanup_fixed_buckets_after_days)
        bugs = Bug.objects.filter(closed__lt=expiry_date)
        for bug in bugs:
            # Deleting the bug causes buckets referring to this bug as well as entries
            # referring these buckets to be deleted as well due to cascading delete.
            # However, if the associated buckets are too large, the cascading delete
            # can easily cause Django to run out of memory so we have to manually
            # delete issues in batches first for large buckets.
            # The reason for Django running OOM here is probably due to the fact that
            # we have a post-delete receiver on CrashEntry that has to be called for
            # every single deleted entry with the full instance. Maybe Django loads
            # a copy of all instances to be deleted into memory for this purpose.
            crashes = CrashEntry.objects.filter(bucket__bug=bug)
            size = crashes.count()
            if size:
                LOG.info(
                    "Removing %d crashes from buckets assigned to bug %s",
                    size,
                    bug.externalId,
                )
            _bulk_delete_crashes(crashes)
            bug.delete()

        # Select all entries that are older than x days and either not in any bucket
        # or the bucket has no bug associated with it. If the bucket has a bug
        # associated then we would want to keep entries around until the bug is fixed
        # (they will be deleted when the bucket is deleted).
        #
        # Again, for the same reason as mentioned above, we have to delete entries in
        # batches.
        expiry_date = sod - timedelta(days=cleanup_crashes_after_days)
        crashes = CrashEntry.objects.filter(created__lt=expiry_date, bucket__bug=None)
        size = crashes.count()
        if size:
            LOG.info("Removing %d old, unbucketed crashes", size)
        _bulk_delete_crashes(crashes)

        # Select all buckets that are empty and delete them
        for bucket in Bucket.objects.annotate(size=Count("crashentry")).filter(
            size=0, permanent=False
        ):
            LOG.info("Removing empty bucket %d", bucket.id)
            bucket.delete()

        # Cleanup all bugs that don't belong to any bucket anymore
        orphan_bugs = Bug.objects.filter(bucket__isnull=True)
        orphan_bug_count = orphan_bugs.count()
        if orphan_bug_count:
            LOG.info("Removing %d orphaned Bug objects", orphan_bug_count)
            orphan_bugs.delete()
