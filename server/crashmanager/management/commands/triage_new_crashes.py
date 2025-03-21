from django.core.management import BaseCommand, call_command

from crashmanager.models import CrashEntry


class Command(BaseCommand):
    help = (
        "Iterates over all unbucketed crash entries that have never been triaged "
        "before to assign them into the existing buckets."
    )

    def handle(self, *args, **options):
        entries = CrashEntry.objects.filter(triagedOnce=False, bucket=None).values_list(
            "id", flat=True
        )

        for entry in entries:
            call_command("triage_new_crash", entry)
