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
    #
    # write_only here means don't try to read it automatically in super().to_native()
    platform = serializers.CharField(max_length=63, write_only=True)
    product = serializers.CharField(max_length=63, write_only=True)
    product_version = serializers.CharField(max_length=63, required=False, write_only=True)
    os = serializers.CharField(max_length=63, write_only=True)
    client = serializers.CharField(max_length=255, write_only=True)
    tool = serializers.CharField(max_length=63, write_only=True)
    testcase = serializers.CharField(required=False)
    testcase_ext = serializers.CharField(required=False, write_only=True)
    testcase_quality = serializers.IntegerField(required=False, default=0, write_only=True)
    testcase_isbinary = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = CrashEntry
        fields = (
                  'rawStdout', 'rawStderr', 'rawCrashData', 'metadata',
                  'testcase', 'testcase_ext', 'testcase_quality', 'testcase_isbinary',
                  'platform', 'product', 'product_version', 'os', 'client', 'tool',
                  'env', 'args', 'bucket', 'id'
                  )
        read_only_fields = ('bucket', 'id')

    def to_native(self, obj):
        '''
        Serialize (flatten) our object. We need custom flattening because we
        want the foreign relationships of our object to be flattened into our
        object by name. Furthermore, we display the testcase here if it is
        not binary.
        '''
        serialized = super(CrashEntrySerializer, self).to_native(obj)
        if obj != None:
            serialized["product"] = obj.product.name
            if obj.product.version:
                serialized["product_version"] = obj.product.version

            serialized["os"] = obj.os.name
            serialized["platform"] = obj.platform.name
            serialized["client"] = obj.client.name
            serialized["tool"] = obj.tool.name

            if obj.testcase:
                serialized["testcase_isbinary"] = obj.testcase.isBinary
                serialized["testcase_quality"] = obj.testcase.quality
                serialized["testcase"] = str(obj.testcase.test)

        return serialized

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

        product = attrs.pop('product', None)
        product_version = attrs.pop('product_version', None)
        platform = attrs.pop('platform', None)
        os = attrs.pop('os', None)
        client = attrs.pop('client', None)
        tool = attrs.pop('tool', None)
        testcase = attrs.pop('testcase', None)
        testcase_ext = attrs.pop('testcase_ext', None)
        testcase_quality = attrs.pop('testcase_quality', 0)
        testcase_isbinary = attrs.pop('testcase_isbinary', False)

        # Parse the incoming data using the crash signature package from FTB
        configuration = ProgramConfiguration(product, platform, os, product_version)
        crashInfo = CrashInfo.fromRawCrashData(attrs['rawStdout'], attrs['rawStderr'], configuration, attrs['rawCrashData'])

        # Populate certain fields here from the CrashInfo object we just got
        if crashInfo.crashAddress != None:
            attrs['crashAddress'] = hex(crashInfo.crashAddress)
        attrs['shortSignature'] = crashInfo.createShortSignature()

        def createOrGetModelByName(model, attrs):
            '''
            Generically determine if the given model with the given attributes
            already exists in our database. If so, return that object, otherwise
            create it on the fly.
            
            @type model: Class
            @param model: The model to use for filtering and instantiating
            
            @type attrs: dict
            @param attrs: Dictionary of attributes to use for filtering/instantiating
            
            @rtype: model
            @return The model instance
            '''
            objs = model.objects.filter(**attrs)

            if len(objs) > 1:
                raise MultipleObjectsReturned("Multiple objects with same keyword combination in database!")

            if len(objs) == 0:
                dbobj = model(**attrs)
                dbobj.save()
                return dbobj
            else:
                return objs.first()

        # Get or instantiate objects for product, platform, os, client and tool
        attrs['product'] = createOrGetModelByName(Product, { 'name' : product, 'version' : product_version })
        attrs['platform'] = createOrGetModelByName(Platform, { 'name' : platform })
        attrs['os'] = createOrGetModelByName(OS, { 'name' : os })
        attrs['client'] = createOrGetModelByName(Client, { 'name' : client })
        attrs['tool'] = createOrGetModelByName(Tool, { 'name' : tool })

        # If a testcase is supplied, create a testcase object and store it
        if testcase:
            if testcase_ext == None:
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
    bug = serializers.SlugRelatedField(slug_field="externalId", read_only=True)
    # write_only here means don't try to read it automatically in super().to_native()
    # size and best_quality are annotations, so must be set manually
    size = serializers.IntegerField(write_only=True)
    best_quality = serializers.IntegerField(write_only=True)

    class Meta:
        model = Bucket
        fields = ('best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription', 'signature', 'size')
        read_only_fields = ('id', 'frequent', 'permanent', 'shortDescription', 'signature')

    def to_native(self, obj):
        serialized = super(BucketSerializer, self).to_native(obj)
        if obj is not None:
            serialized["size"] = obj.size
            serialized["best_quality"] = obj.quality
            # setting best_crash requires knowing whether the bucket query was restricted eg. by tool
            # see note in BucketAnnotateFilterBackend

        return serialized
