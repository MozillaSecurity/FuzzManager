from django.core.management.base import NoArgsCommand
from crashmanager.models import CrashEntry, Bucket, Bug
from django.db.models.aggregates import Count
from datetime import datetime, timedelta
from django.conf import settings

class Command(NoArgsCommand):
    help = "Cleanup old crash entries."
    def handle_noargs(self, **options):
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
        buckets = Bucket.objects.annotate(size=Count('crashentry')).filter(size=0)
        for bucket in buckets:
            bucket.delete()
            
        # Select all entries that are older than x days
        expiryDate = datetime.now().date() - timedelta(days=cleanup_crashes_after_days)
        entries = CrashEntry.objects.filter(created__lt = expiryDate)
        for entry in entries:
            entry.delete()