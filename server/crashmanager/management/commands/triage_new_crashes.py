from django.core.management.base import NoArgsCommand
from crashmanager.models import CrashEntry, Bucket

class Command(NoArgsCommand):
    help = "Iterates over all unbucketed crash entries and tries to assign them into the existing buckets."
    def handle_noargs(self, **options):
        entries = CrashEntry.objects.filter(bucket=None)
        buckets = Bucket.objects.all()
    
        for bucket in buckets:
            signature = bucket.getSignature()
            for entry in entries:
                if signature.matches(entry.getCrashInfo()):
                    entry.bucket = bucket
                    entry.save()