from django.core.management.base import NoArgsCommand
from crashmanager.models import CrashEntry, Bucket
from crashmanager.management.common import mgmt_lock_required

class Command(NoArgsCommand):
    help = "Iterates over all unbucketed crash entries and tries to assign them into the existing buckets."
    @mgmt_lock_required
    def handle_noargs(self, **options):
        entries = CrashEntry.objects.filter(bucket=None)
        buckets = Bucket.objects.all()
    
        for bucket in buckets:
            signature = bucket.getSignature()
            needTest = signature.matchRequiresTest()
            
            for entry in entries:
                if signature.matches(entry.getCrashInfo(attachTestcase=needTest)):
                    entry.bucket = bucket
                    entry.save()