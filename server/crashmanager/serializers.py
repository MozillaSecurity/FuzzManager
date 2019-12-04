import base64
from django.core.exceptions import MultipleObjectsReturned  # noqa
from django.core.files.base import ContentFile
from django.forms import widgets  # noqa
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
    product_version = serializers.CharField(source='product.version', max_length=127, required=False, allow_blank=True)
    os = serializers.CharField(source='os.name', max_length=63)
    client = serializers.CharField(source='client.name', max_length=255)
    tool = serializers.CharField(source='tool.name', max_length=63)
    testcase = serializers.CharField(source='testcase.test', required=False)
    testcase_ext = serializers.CharField(required=False, allow_blank=True)
    testcase_size = serializers.IntegerField(source='testcase.size', required=False, default=0)
    testcase_quality = serializers.IntegerField(source='testcase.quality', required=False, default=0)
    testcase_isbinary = serializers.BooleanField(source='testcase.isBinary', required=False, default=False)

    def __init__(self, *args, **kwargs):

        include_raw = kwargs.pop('include_raw', True)

        super(CrashEntrySerializer, self).__init__(*args, **kwargs)

        if not include_raw:
            for field_name in ('rawCrashData', 'rawStdout', 'rawStderr'):
                self.fields.pop(field_name)

    class Meta:
        model = CrashEntry
        fields = (
            'rawStdout', 'rawStderr', 'rawCrashData', 'metadata',
            'testcase', 'testcase_ext', 'testcase_size', 'testcase_quality', 'testcase_isbinary',
            'platform', 'product', 'product_version', 'os', 'client', 'tool',
            'env', 'args', 'bucket', 'id', 'shortSignature', 'crashAddress',
        )
        ordering = ['-id']
        read_only_fields = ('bucket', 'id', 'shortSignature', 'crashAddress')

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

        attrs['product'] = Product.objects.get_or_create(**attrs['product'])[0]
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
            attrs['crashAddress'] = '0x%x' % crashInfo.crashAddress
        attrs['shortSignature'] = crashInfo.createShortSignature()
        attrs['shortSignature'] = attrs['shortSignature'][:CrashEntry._meta.get_field('shortSignature').max_length]

        # If a testcase is supplied, create a testcase object and store it
        if 'test' in attrs['testcase']:

            testcase = attrs['testcase']
            testcase_ext = attrs.pop('testcase_ext', None)
            testcase_size = testcase.get('size', 0)
            testcase_quality = testcase.get('quality', 0)
            testcase_isbinary = testcase.get('isBinary', False)
            testcase = testcase['test']

            if testcase_ext is None:
                raise RuntimeError("Must provide testcase extension when providing testcase")

            h = hashlib.new('sha1')
            if testcase_isbinary:
                testcase = base64.b64decode(testcase)
                h.update(testcase)
            else:
                h.update(repr(testcase).encode("utf-8"))

            if not testcase_size:
                testcase_size = len(testcase)

            dbobj = TestCase(quality=testcase_quality, isBinary=testcase_isbinary, size=testcase_size)
            dbobj.test.save("%s.%s" % (h.hexdigest(), testcase_ext), ContentFile(testcase))
            dbobj.save()
            attrs['testcase'] = dbobj
        else:
            attrs['testcase'] = None

        try:
            # Create our CrashEntry instance
            return super(CrashEntrySerializer, self).create(attrs)
        except:  # noqa
            if attrs['testcase'] is not None:
                attrs['testcase'].delete()
            raise


class BucketSerializer(serializers.ModelSerializer):
    bug = serializers.CharField(source='bug.externalId', default=None)
    # write_only here means don't try to read it automatically in super().to_representation()
    # size and best_quality are annotations, so must be set manually
    size = serializers.IntegerField(write_only=True)
    best_quality = serializers.IntegerField(write_only=True)

    class Meta:
        model = Bucket
        fields = ('best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription', 'signature', 'size')
        ordering = ['-id']
        read_only_fields = ('id', 'frequent', 'permanent', 'shortDescription', 'signature')

    def to_representation(self, obj):
        serialized = super(BucketSerializer, self).to_representation(obj)
        serialized['size'] = obj.size
        serialized['best_quality'] = obj.quality
        # setting best_crash requires knowing whether the bucket query was restricted eg. by tool
        # see note in BucketAnnotateFilterBackend
        return serialized
