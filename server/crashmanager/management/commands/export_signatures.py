import json
import os
import shutil
from tempfile import mkdtemp
from zipfile import ZipFile

from django.core.management.base import LabelCommand
from django.db.models.aggregates import Count, Min

from crashmanager.management.common import mgmt_lock_required
from crashmanager.models import CrashEntry, Bucket


class Command(LabelCommand):
    help = "Export signatures and their metadata."
    @mgmt_lock_required
    def handle_label(self, label, **options):
        
        tmpDir = mkdtemp(prefix="fuzzmanager-sigexport")
        
        try:
            with ZipFile(label, 'w') as zipFile:
                for bucket in Bucket.objects.annotate(size=Count('crashentry'), quality=Min('crashentry__testcase__quality')):
                    try:
                        bucket.bestEntry = CrashEntry.objects.filter(bucket=bucket.pk).filter(testcase__quality=bucket.quality).order_by('testcase__size', '-created')[0]
                    except IndexError:
                        bucket.bestEntry = None
                        
                    metadata = {}
                    metadata['size'] = bucket.size
                    metadata['shortDescription'] = bucket.shortDescription
                    metadata['frequent'] = bucket.frequent
                    if bucket.bug is not None:
                        metadata['bug__id'] = bucket.bug.externalId 
                        
                    if bucket.bestEntry is not None and bucket.bestEntry.testcase is not None:
                        metadata['testcase__quality'] = bucket.bestEntry.testcase.quality
                        metadata['testcase__size'] = bucket.bestEntry.testcase.size
                    
                    sigFileName = "%d.signature" % bucket.pk
                    metaFileName = "%d.metadata" % bucket.pk
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
