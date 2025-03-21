from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Min

from crashmanager.models import Bucket, BucketStatistics, CrashEntry, Tool


class Command(BaseCommand):
    help = "Populate or rebuild bucket statistics table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Clear existing statistics before rebuilding",
        )

    def handle(self, *args, **options):
        if options["force"]:
            self.stdout.write("Clearing existing statistics...")
            BucketStatistics.objects.all().delete()

        self.stdout.write("Processing buckets...")
        buckets = Bucket.objects.iterator()
        stats_created = 0

        for bucket in buckets:
            tools = Tool.objects.filter(
                id__in=CrashEntry.objects.filter(bucket=bucket).values("tool")
            ).distinct()

            for tool in tools:
                with transaction.atomic():
                    crashes = CrashEntry.objects.filter(bucket=bucket, tool=tool)
                    stats = CrashEntry.deferRawFields(crashes).aggregate(
                        size=Count("id"), quality=Min("testcase__quality")
                    )

                    BucketStatistics.objects.update_or_create(
                        bucket=bucket,
                        tool=tool,
                        defaults={"size": stats["size"], "quality": stats["quality"]},
                    )
                    stats_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created/updated {stats_created} bucket statistics"
            )
        )
