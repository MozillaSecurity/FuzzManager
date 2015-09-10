from django.core.management.base import NoArgsCommand
from crashmanager.models import CrashEntry, Bucket
from crashmanager.management.common import mgmt_lock_required
from datetime import datetime, timedelta
from django.conf import settings

class Command(NoArgsCommand):
    help = "Iterates over all unbucketed crash entries since a certain time period and tries to assign them into the existing buckets."
    @mgmt_lock_required
    def handle_noargs(self, **options):
        triage_bugs_since_minutes = getattr(settings, 'TRIAGE_BUGS_SINCE_MINUTES', 15)
        sinceDate = datetime.now().date() - timedelta(minutes=triage_bugs_since_minutes)
        entries = CrashEntry.objects.filter(created__gte = sinceDate, bucket=None)
        buckets = Bucket.objects.all()
    
        for bucket in buckets:
            signature = bucket.getSignature()
            needTest = signature.matchRequiresTest()
            
            for entry in entries:
                if signature.matches(entry.getCrashInfo(attachTestcase=needTest)):
                    entry.bucket = bucket
                    entry.save()