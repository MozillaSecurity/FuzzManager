from django.core.management import BaseCommand, call_command

from reportmanager.models import ReportEntry


class Command(BaseCommand):
    help = (
        "Iterates over all unbucketed report entries that have never been triaged "
        "before to assign them into the existing buckets."
    )

    def handle(self, *args, **options):
        entries = ReportEntry.objects.filter(
            triagedOnce=False, bucket=None
        ).values_list("id", flat=True)

        for entry in entries:
            call_command("triage_new_report", entry)

        # This query ensures that all issues that have been bucketed manually before
        # the server had a chance to triage them will have their triageOnce flag set,
        # so the hourglass in the UI isn't displayed anymore.
        ReportEntry.deferRawFields(ReportEntry.objects.exclude(bucket=None)).update(
            triagedOnce=True
        )
