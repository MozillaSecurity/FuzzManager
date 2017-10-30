import base64
from django.core.exceptions import MultipleObjectsReturned
from django.core.files.base import ContentFile
from django.forms import widgets
import hashlib
from rest_framework import serializers
from rest_framework.exceptions import APIException

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from crashmanager.models import CrashEntry, Bucket, Platform, Product, OS, TestCase, Client, Tool

class InvalidArgumentException(APIException):
    status_code = 400

class CrashEntrySerializer(serializers.ModelSerializer):
    # We need to redefine several fields explicitly because we flatten our
    # foreign keys into these fields instead of using primary keys, hyperlinks
    # or slug fields. All of the other solutions would require the client to
    # create these instances first and issue multiple requests in total.
    platform = serializers.CharField(source='platform.name', max_length=63)
    product = serializers.CharField(source='product.name', max_length=63)
    product_version = serializers.CharField(source='product.version', max_length=63, required=False, allow_blank=True)
    os = serializers.CharField(source='os.name', max_length=63)
    client = serializers.CharField(source='client.name', max_length=255)
    tool = serializers.CharField(source='tool.name', max_length=63)
    testcase = serializers.CharField(source='testcase.test', required=False)
    testcase_ext = serializers.CharField(required=False, allow_blank=True)
    testcase_quality = serializers.IntegerField(source='testcase.quality', required=False, default=0)
    testcase_isbinary = serializers.BooleanField(source='testcase.isBinary', required=False, default=False)

    class Meta:
        model = CrashEntry
        fields = (
                  'rawStdout', 'rawStderr', 'rawCrashData', 'metadata',
                  'testcase', 'testcase_ext', 'testcase_quality', 'testcase_isbinary',
                  'platform', 'product', 'product_version', 'os', 'client', 'tool',
                  'env', 'args', 'bucket', 'id'
                  )
        read_only_fields = ('bucket', 'id')

    def create(self, attrs):
        '''
        Create a CrashEntry instance based on the given dictionary of values
        received. We need to unflatten foreign relationships like product,
        platform, os and client and create the foreign objects on the fly
        if they don't exist in our database yet.
        '''
        missing_keys = {'rawStdout', 'rawStderr', 'rawCrashData'} - set(attrs.keys())
        if missing_keys:
            raise InvalidArgumentException({key: ["This field is required."] for key in missing_keys})

        try:
            attrs['product'] = Product.objects.get_or_create(**attrs['product'])[0]
        except Product.MultipleObjectsReturned:
            attrs['product'] = Product.objects.filter(**attrs['product']).first()

        attrs['platform'] = Platform.objects.get_or_create(**attrs['platform'])[0]
        attrs['os'] = OS.objects.get_or_create(**attrs['os'])[0]
        attrs['client'] = Client.objects.get_or_create(**attrs['client'])[0]
        attrs['tool'] = Tool.objects.get_or_create(**attrs['tool'])[0]

        # Parse the incoming data using the crash signature package from FTB
        configuration = ProgramConfiguration(attrs['product'].name, attrs['platform'].name, attrs['os'].name,
                                             attrs['product'].version)
        crashInfo = CrashInfo.fromRawCrashData(attrs['rawStdout'], attrs['rawStderr'], configuration,
                                               attrs['rawCrashData'])

        # Populate certain fields here from the CrashInfo object we just got
        if crashInfo.crashAddress is not None:
            attrs['crashAddress'] = hex(crashInfo.crashAddress)
        attrs['shortSignature'] = crashInfo.createShortSignature()

        # If a testcase is supplied, create a testcase object and store it
        if 'test' in attrs['testcase']:

            testcase = attrs['testcase']
            testcase_ext = attrs.pop('testcase_ext', None)
            testcase_quality = testcase.get('quality', 0)
            testcase_isbinary = testcase.get('isBinary', False)
            testcase = testcase['test']

            if testcase_ext is None:
                raise RuntimeError("Must provide testcase extension when providing testcase")

            if testcase_isbinary:
                testcase = base64.b64decode(testcase)

            h = hashlib.new('sha1')
            if testcase_isbinary:
                h.update(str(testcase))
            else:
                h.update(repr(testcase))

            dbobj = TestCase(quality=testcase_quality, isBinary=testcase_isbinary, size=len(testcase))
            dbobj.test.save("%s.%s" % (h.hexdigest(), testcase_ext), ContentFile(testcase))
            dbobj.save()
            attrs['testcase'] = dbobj
        else:
            attrs['testcase'] = None

        # Create our CrashEntry instance
        return super(CrashEntrySerializer, self).create(attrs)


class BucketSerializer(serializers.ModelSerializer):
    bug = serializers.CharField(source='bug.externalId')
    # write_only here means don't try to read it automatically in super().to_representation()
    # size and best_quality are annotations, so must be set manually
    size = serializers.IntegerField(write_only=True)
    best_quality = serializers.IntegerField(write_only=True)

    class Meta:
        model = Bucket
        fields = ('best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription', 'signature', 'size')
        read_only_fields = ('id', 'frequent', 'permanent', 'shortDescription', 'signature')

    def to_representation(self, obj):
        serialized = super(BucketSerializer, self).to_representation(obj)
        serialized['size'] = obj.size
        serialized['best_quality'] = obj.quality
        # setting best_crash requires knowing whether the bucket query was restricted eg. by tool
        # see note in BucketAnnotateFilterBackend
        return serialized
