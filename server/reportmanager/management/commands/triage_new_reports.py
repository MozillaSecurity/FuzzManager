from django.core.management import BaseCommand, call_command

from reportmanager.models import ReportEntry


class Command(BaseCommand):
    help = (
        "Iterates over all unbucketed report entries that have never been triaged "
        "before to assign them into the existing buckets."
    )

    def handle(self, *args, **options):
        for entry in ReportEntry.objects.filter(bucket__isnull=True).values_list(
            "id", flat=True
        ):
            call_command("triage_new_report", entry)
