import logging
from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand, CommandError  # noqa
from django.db.models.aggregates import Count
from django.utils import timezone

from reportmanager.models import Bucket, Bug, ReportEntry

LOG = logging.getLogger("fm.reportmanager.cleanup_old_reports")


class Command(BaseCommand):
    help = "Cleanup old report entries."

    def handle(self, *args, **options):
        cleanup_reports_after_days = getattr(settings, "CLEANUP_REPORTS_AFTER_DAYS", 14)
        cleanup_fixed_buckets_after_days = getattr(
            settings, "CLEANUP_FIXED_BUCKETS_AFTER_DAYS", 3
        )

        # Select all buckets that have been closed for x days
        now = timezone.now()
        expiry_date = now - timedelta(
            days=cleanup_fixed_buckets_after_days,
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond,
        )
        bugs = Bug.objects.filter(closed__lt=expiry_date)
        for bug in bugs:
            # Deleting the bug causes buckets referring to this bug as well as entries
            # referring these buckets to be deleted as well due to cascading delete.
            # However, if the associated buckets are too large, the cascading delete
            # can easily cause Django to run out of memory so we have to manually
            # delete issues in batches first for large buckets.
            # The reason for Django running OOM here is probably due to the fact that
            # we have a post-delete receiver on ReportEntry that has to be called for
            # every single deleted entry with the full instance. Maybe Django loads
            # a copy of all instances to be deleted into memory for this purpose.
            report_count = ReportEntry.objects.filter(bucket__bug=bug).count()
            if report_count:
                LOG.info(
                    "Removing %d ReportEntry objects from buckets assigned to bug %s",
                    report_count,
                    bug.external_id,
                )
            while report_count > 500:
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

                pks = list(
                    ReportEntry.objects.filter(bucket__bug=bug).values_list(
                        "pk", flat=True
                    )[:500]
                )
                ReportEntry.objects.filter(pk__in=pks).delete()
                report_count = ReportEntry.objects.filter(bucket__bug=bug).count()

            bug.delete()

        # Select all buckets that are empty and delete them
        for bucket in Bucket.objects.annotate(size=Count("reportentry")).filter(
            size=0, bug=None, permanent=False
        ):
            LOG.info("Removing empty bucket %d", bucket.id)
            bucket.delete()

        # Select all entries that are older than x days and either not in any bucket
        # or the bucket has no bug associated with it. If the bucket has a bug
        # associated then we would want to keep entries around until the bug is fixed
        # (they will be deleted when the bucket is deleted).
        #
        # Again, for the same reason as mentioned above, we have to delete entries in
        # batches.
        expiry_date = now - timedelta(
            days=cleanup_reports_after_days,
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond,
        )
        old_reports = ReportEntry.objects.filter(
            created__lt=expiry_date, bucket__bug=None
        ).count()
        if old_reports:
            LOG.info("Removing %d old, unbucketed reports", old_reports)
        while old_reports:
            pks = list(
                ReportEntry.objects.filter(
                    created__lt=expiry_date, bucket__bug=None
                ).values_list("pk", flat=True)[:500]
            )
            ReportEntry.objects.filter(pk__in=pks).delete()
            old_reports = ReportEntry.objects.filter(
                created__lt=expiry_date, bucket__bug=None
            ).count()

        # Cleanup all bugs that don't belong to any bucket anymore
        orphan_bugs = Bug.objects.filter(bucket__isnull=True)
        orphan_bug_count = orphan_bugs.count()
        if orphan_bug_count:
            LOG.info("Removing %d orphaned Bug objects", orphan_bug_count)
            orphan_bugs.delete()
