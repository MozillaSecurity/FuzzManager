from django.db import models

class Platform(models.Model):
    name = models.CharField(max_length=63)

class Product(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127)
    
class OS(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127)
    
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
    bug = models.ForeignKey(Bug)
    signature = models.TextField()

class CrashEntry(models.Model):
    platform = models.ForeignKey(Platform)
    product = models.ForeignKey(Product)
    os = models.ForeignKey(OS)
    testcase = models.ForeignKey(TestCase)
    client = models.ForeignKey(Client)
    bucket = models.ForeignKey(Bucket)
    rawStdout = models.TextField()
    rawStderr = models.TextField()
    rawCrashData = models.TextField()
    metadata = models.TextField()


    
