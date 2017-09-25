from django.core.management.base import NoArgsCommand
from crashmanager.models import CrashEntry, Bucket, Bug
from django.db.models.aggregates import Count
from datetime import datetime, timedelta
from django.conf import settings
from crashmanager.management.common import mgmt_lock_required
import warnings

class Command(NoArgsCommand):
    help = "Cleanup old crash entries."
    @mgmt_lock_required
    def handle_noargs(self, **options):
        # Suppress warnings about native datetime vs. timezone
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*received a naive datetime.*")

        cleanup_crashes_after_days = getattr(settings, 'CLEANUP_CRASHES_AFTER_DAYS', 14)
        cleanup_fixed_buckets_after_days = getattr(settings, 'CLEANUP_FIXED_BUCKETS_AFTER_DAYS', 3)

        # Select all buckets that have been closed for x days
        expiryDate = datetime.now().date() - timedelta(days=cleanup_fixed_buckets_after_days)
        bugs = Bug.objects.filter(closed__lt = expiryDate)
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
            while CrashEntry.objects.filter(bucket__bug = bug).count() > 500:
                # Deleting things in buckets is complicated:
                #
                # Attempting to combine a subset (LIMIT) with a delete yields
                #   "Cannot use 'limit' or 'offset' with delete."
                #
                # Using a nested query with pk_in=<filter query> yields
                #   "This version of MySQL doesn't yet support 'LIMIT & IN/ALL/ANY/SOME subquery'"

                # So the only way we have left is to manually select a given amount of pks
                # and store them in a list to use pk__in with the list and a DELETE query.

                pks = list(CrashEntry.objects.filter(bucket__bug = bug).values_list('pk')[:500])
                CrashEntry.objects.filter(pk__in=pks).delete()

            bug.delete()

        # Select all buckets that are empty and delete them
        buckets = Bucket.objects.annotate(size=Count('crashentry')).filter(size=0, bug=None, permanent=False)
        for bucket in buckets:
            bucket.delete()

        # Select all entries that are older than x days and either not in any bucket
        # or the bucket has no bug associated with it. If the bucket has a bug associated
        # then we would want to keep entries around until the bug is fixed (they will be
        # deleted when the bucket is deleted).
        #
        # Again, for the same reason as mentioned above, we have to delete entries in batches.
        expiryDate = datetime.now().date() - timedelta(days=cleanup_crashes_after_days)
        while CrashEntry.objects.filter(created__lt = expiryDate, bucket__bug = None).count() > 0:
            pks = list(CrashEntry.objects.filter(created__lt = expiryDate, bucket__bug = None).values_list('pk')[:500])
            CrashEntry.objects.filter(pk__in=pks).delete()

        # Cleanup all bugs that don't belong to any bucket anymore
        bugs = Bug.objects.all()
        associatedBugIds = Bucket.objects.values_list('bug', flat=True)
        for bug in bugs:
            if not bug.pk in associatedBugIds:
                bug.delete()
