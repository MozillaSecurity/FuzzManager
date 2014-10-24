from django.db import models
from django.utils import timezone

class Platform(models.Model):
    name = models.CharField(max_length=63)

class Product(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)
    
class OS(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)
    
class TestCase(models.Model):
    test = models.BinaryField()
    isBinary = models.BooleanField(default=False)

class Client(models.Model):
    name = models.CharField(max_length=255)
    
class Bug(models.Model):
    NONE=0
    BUGZILLA=1
    EXT_TYPE_CHOICES=(
        (NONE, 'None'),
        (BUGZILLA, 'Bugzilla'),
    )
    externalId = models.CharField(max_length=255, blank=True)
    externalType = models.IntegerField(choices=EXT_TYPE_CHOICES, default=NONE)
    reported = models.BooleanField(default=False)
    
class Bucket(models.Model):
    bug = models.ForeignKey(Bug, blank=True, null=True)
    signature = models.TextField()
    shortDescription = models.CharField(max_length=1023, blank=True)

class CrashEntry(models.Model):
    created = models.DateTimeField(default=timezone.now)
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
    crashAddress = models.CharField(max_length=255, blank=True)
    shortSignature = models.CharField(max_length=255, blank=True)


    
