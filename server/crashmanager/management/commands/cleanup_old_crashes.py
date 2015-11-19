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
            # This delete causes buckets referring to this bug, as well as entries
            # referring these buckets, to be deleted as well due to cascading delete.
            bug.delete()
            
        # Select all buckets that are empty and delete them
        buckets = Bucket.objects.annotate(size=Count('crashentry')).filter(size=0, bug=None)
        for bucket in buckets:
            bucket.delete()
            
        # Select all entries that are older than x days and either not in any bucket
        # or the bucket has no bug associated with it. If the bucket has a bug associated
        # then we would want to keep entries around until the bug is fixed (they will be
        # deleted when the bucket is deleted).
        expiryDate = datetime.now().date() - timedelta(days=cleanup_crashes_after_days)
        entries = CrashEntry.objects.filter(created__lt = expiryDate, bucket__bug = None)
        for entry in entries:
            entry.delete()
            
        # Cleanup all bugs that don't belong to any bucket anymore
        bugs = Bug.objects.all()
        associatedBugIds = Bucket.objects.values_list('bug', flat=True)
        for bug in bugs:
            if not bug.pk in associatedBugIds:
                bug.delete()