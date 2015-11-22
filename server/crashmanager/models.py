from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from django.contrib.auth.models import User as DjangoUser

from FTB.Signatures.CrashSignature import CrashSignature
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration

import json
import re

class Tool(models.Model):
    name = models.CharField(max_length=63)

class Platform(models.Model):
    name = models.CharField(max_length=63)

class Product(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)
    
class OS(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)
    
class TestCase(models.Model):
    test = models.FileField(storage=FileSystemStorage(location=getattr(settings, 'TEST_STORAGE', None)), upload_to="tests")
    size = models.IntegerField(default=0)
    quality = models.IntegerField(default=0)
    isBinary = models.BooleanField(default=False)
    
    def __init__(self, *args, **kwargs):
        # This variable can hold the testcase data temporarily
        self.content = None
        
        # For performance reasons we do not load the test here
        # automatically. You must call the loadTest method if you
        # want to access the test content
        
        super(TestCase, self).__init__(*args, **kwargs)
    
    def loadTest(self):
        self.test.open(mode='rb')
        self.content = self.test.read()
        self.test.close()
        
    def storeTestAndSave(self):
        self.size = len(self.content)
        self.test.open(mode='w')
        self.test.write(self.content)
        self.test.close()
        self.save()

class Client(models.Model):
    name = models.CharField(max_length=255)
    
class BugProvider(models.Model):
    classname = models.CharField(max_length=255, blank=False)
    hostname = models.CharField(max_length=255, blank=False)
    
    # This is used to annotate bugs with the URL linking to them
    urlTemplate = models.CharField(max_length=1023, blank=False)
    
    def getInstance(self):
        # Dynamically instantiate the provider as requested
        providerModule = __import__('crashmanager.Bugtracker.%s' % self.classname, fromlist=[self.classname])
        providerClass = getattr(providerModule, self.classname)
        return providerClass(self.pk, self.hostname)

class Bug(models.Model):
    externalId = models.CharField(max_length=255, blank=True)
    externalType = models.ForeignKey(BugProvider)
    closed = models.DateTimeField(blank=True, null=True)

class Bucket(models.Model):
    bug = models.ForeignKey(Bug, blank=True, null=True)
    signature = models.TextField()
    shortDescription = models.CharField(max_length=1023, blank=True)
    frequent = models.BooleanField(blank=False, default=False)
    permanent = models.BooleanField(blank=False, default=False)

    def getSignature(self):
        return CrashSignature(self.signature)
    
    def save(self, *args, **kwargs):
        # Sanitize signature line endings so we end up with the same hash
        # TODO: We might want to just parse the JSON here, and re-serialize
        # it to a canonical string representation.
        self.signature = self.signature.replace(r"\r\n", r"\n")
        super(Bucket, self).save(*args, **kwargs)

class CrashEntry(models.Model):
    created = models.DateTimeField(default=timezone.now)
    tool = models.ForeignKey(Tool)
    platform = models.ForeignKey(Platform)
    product = models.ForeignKey(Product)
    os = models.ForeignKey(OS)
    testcase = models.ForeignKey(TestCase, blank=True, null=True)
    client = models.ForeignKey(Client)
    bucket = models.ForeignKey(Bucket, blank=True, null=True)
    rawStdout = models.TextField(blank=True)
    rawStderr = models.TextField(blank=True)
    rawCrashData = models.TextField(blank=True)
    metadata = models.TextField(blank=True)
    env = models.TextField(blank=True)
    args = models.TextField(blank=True)
    crashAddress = models.CharField(max_length=255, blank=True)
    crashAddressNumeric = models.BigIntegerField(blank=True, null=True)
    shortSignature = models.CharField(max_length=255, blank=True)
    
    def __init__(self, *args, **kwargs):
        # These variables can hold temporarily deserialized data
        self.argsList = None
        self.envList = None
        self.metadataList = None
        
        # For performance reasons we do not deserialize these fields
        # automatically here. You need to explicitly call the 
        # deserializeFields method if you need this data.
        
        super(CrashEntry, self).__init__(*args, **kwargs)
        
    def save(self, *args, **kwargs):
        if self.pk is None and not getattr(settings, 'DB_ISUTF8MB4', False):
            # Replace 4-byte UTF-8 characters with U+FFFD if our database
            # doesn't support them. By default, MySQL utf-8 does not support these.  
            utf8_4byte_re = re.compile(u'[^\u0000-\uD7FF\uE000-\uFFFF]', re.UNICODE)
            def sanitize_utf8(s):
                if not isinstance(s, unicode):
                    s = unicode(s, 'utf-8')
                return utf8_4byte_re.sub(u"\uFFFD", s)
            
            self.rawStdout = sanitize_utf8(self.rawStdout)
            self.rawStderr = sanitize_utf8(self.rawStderr)
            self.rawCrashData = sanitize_utf8(self.rawCrashData)
        
        # Reserialize data, then call regular save method
        if self.argsList:
            self.args = json.dumps(self.argsList)
    
        if self.envList:
            envDict = dict([x.split("=", 1) for x in self.envList])
            self.env = json.dumps(envDict)
    
        if self.metadataList:
            metadataDict = dict([x.split("=", 1) for x in self.metadataList])
            self.metadata = json.dumps(metadataDict)
        
        # When we have a crash address, keep the numeric crash address field in
        # sync so we can search easily by crash address including ranges
        if self.crashAddress:
            self.crashAddressNumeric = long(self.crashAddress, 16)
            
            # We need to possibly convert the numeric crash address from unsigned
            # to signed in order to store it in the database.
            if (self.crashAddressNumeric > (2**63-1)):
                self.crashAddressNumeric -= 2**64

        if len(self.shortSignature) > 255:
            self.shortSignature = self.shortSignature[0:255]
        
        super(CrashEntry, self).save(*args, **kwargs)
    
    def deserializeFields(self):
        if self.args:
            self.argsList = json.loads(self.args)
    
        if self.env:
            envDict = json.loads(self.env)
            self.envList = ["%s=%s" % (s,envDict[s]) for s in envDict.keys()]
    
        if self.metadata:
            metadataDict = json.loads(self.metadata)
            self.metadataList = ["%s=%s" % (s,metadataDict[s]) for s in metadataDict.keys()]
    
    
    def getCrashInfo(self, attachTestcase=False):
        # TODO: This should be cached at some level
        # TODO: Need to include environment and program arguments here
        configuration = ProgramConfiguration(self.product.name, self.platform.name, self.os.name, self.product.version)
        crashInfo = CrashInfo.fromRawCrashData(self.rawStdout, self.rawStderr, configuration, self.rawCrashData)
        
        if attachTestcase and self.testcase != None and not self.testcase.isBinary:
            self.testcase.loadTest()
            crashInfo.testcase = self.testcase.content
        
        return crashInfo

# This post_delete handler ensures that the corresponding testcase
# is also deleted when the CrashEntry is gone. It also explicitely
# deletes the file on the filesystem which would otherwise remain.
@receiver(post_delete, sender=CrashEntry)
def CrashEntry_delete(sender, instance, **kwargs):
    if instance.testcase:
        if instance.testcase.test:
            instance.testcase.test.delete(False)
        instance.testcase.delete(False)

class BugzillaTemplate(models.Model):
    name = models.TextField()
    product = models.TextField()
    component = models.TextField()
    summary = models.TextField(blank=True)
    version = models.TextField()
    description = models.TextField(blank=True)
    whiteboard = models.TextField(blank=True)
    keywords = models.TextField(blank=True)
    op_sys = models.TextField(blank=True)
    platform = models.TextField(blank=True)
    priority = models.TextField(blank=True)
    severity = models.TextField(blank=True)
    alias = models.TextField(blank=True)
    cc = models.TextField(blank=True)
    assigned_to = models.TextField(blank=True)
    qa_contact = models.TextField(blank=True)
    target_milestone = models.TextField(blank=True)
    attrs = models.TextField(blank=True)
    security = models.BooleanField(blank=False, default=False)
    security_group = models.TextField(blank=True)
    comment = models.TextField(blank=True)


class User(models.Model):
    user = models.OneToOneField(DjangoUser)
    # Explicitely do not store this as a ForeignKey to e.g. BugzillaTemplate
    # because the bug provider has to decide how to interpret this ID.
    defaultTemplateId = models.IntegerField(default=0)
    defaultProviderId = models.IntegerField(default=1)
    defaultToolsFilter = models.ManyToManyField(Tool)

