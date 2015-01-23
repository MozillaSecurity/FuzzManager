from django.core.management.base import LabelCommand
from crashmanager.models import CrashEntry, Bucket
from django.db.models.aggregates import Count, Min
from crashmanager.management.common import mgmt_lock_required
from tempfile import mkdtemp
import json
import shutil
import os
from zipfile import ZipFile

class Command(LabelCommand):
    help = "Export signatures and their metadata."
    @mgmt_lock_required
    def handle_label(self, label, **options):
        
        tmpDir = mkdtemp(prefix="fuzzmanager-sigexport")
        
        try:
            buckets = Bucket.objects.annotate(size=Count('crashentry'),quality=Min('crashentry__testcase__quality'))
            with ZipFile(label, 'w') as zipFile:
                for bucket in buckets:
                    entries = CrashEntry.objects.filter(bucket=bucket.pk).filter(testcase__quality=bucket.quality).order_by('testcase__size', '-created')
                    bucket.bestEntry = None
                    if entries:
                        bucket.bestEntry = entries[0]
                        
                    metadata = {}
                    metadata['size'] = bucket.size
                    metadata['shortDescription'] = bucket.shortDescription
                    metadata['frequent'] = bucket.frequent
                    if bucket.bug != None:
                        metadata['bug__id'] = bucket.bug.externalId 
                        
                    if bucket.bestEntry != None and bucket.bestEntry.testcase != None:
                        metadata['testcase__quality'] = bucket.bestEntry.testcase.quality
                        metadata['testcase__size'] = bucket.bestEntry.testcase.size
                    
                    sigFileName = str(bucket.pk) + ".signature"
                    metaFileName = str(bucket.pk) + ".metadata"
                    sigFile = os.path.join(tmpDir, sigFileName)
                    metaFile = os.path.join(tmpDir, metaFileName)
                    
                    with open(sigFile, 'w') as f:
                        f.write(bucket.signature)
                        
                    with open(metaFile, 'w') as f:
                        f.write(json.dumps(metadata, indent=4))
            
                    zipFile.write(sigFile, sigFileName)
                    zipFile.write(metaFile, metaFileName)
        finally:
            shutil.rmtree(tmpDir)