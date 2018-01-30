import json
from zipfile import ZipFile

from django.core.management.base import BaseCommand
from django.db.models.aggregates import Count, Min

from crashmanager.management.common import mgmt_lock_required
from crashmanager.models import CrashEntry, Bucket


class Command(BaseCommand):
    help = "Export signatures and their metadata."

    def add_arguments(self, parser):
        parser.add_argument("filename", help="output filename to write signatures zip to")

    @mgmt_lock_required
    def handle(self, filename, **options):

        with ZipFile(filename, 'w') as zipFile:
            for bucket in Bucket.objects.annotate(size=Count('crashentry'),
                                                  quality=Min('crashentry__testcase__quality')):
                bestEntryQuery = (CrashEntry.objects
                                  .filter(bucket_id=bucket.pk)
                                  .filter(testcase__quality=bucket.quality)
                                  .defer('rawCrashData', 'rawStderr', 'rawStdout')
                                  .order_by('testcase__size', '-id'))
                if bestEntryQuery.count():
                    bucket.bestEntry = bestEntryQuery[0]
                else:
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

                zipFile.writestr(sigFileName, bucket.signature)
                zipFile.writestr(metaFileName, json.dumps(metadata, indent=4))
