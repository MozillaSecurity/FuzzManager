import json
import re
from datetime import timedelta
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User as DjangoUser
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Min
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils import timezone
from enumfields import Enum, EnumField
from notifications.signals import notify

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.Signatures.CrashSignature import CrashSignature

if getattr(settings, "USE_CELERY", None):
    from .tasks import triage_new_crash

LOG = getLogger("crashmanager")


class Tool(models.Model):
    name = models.CharField(max_length=63, unique=True)

    def __str__(self):
        return self.name


class Platform(models.Model):
    name = models.CharField(max_length=63, unique=True)


class Product(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_product_version",
            ),
        ]


class OS(models.Model):
    name = models.CharField(max_length=63)
    version = models.CharField(max_length=127, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_os_version",
            ),
        ]


class TestCase(models.Model):
    test = models.FileField(
        storage=FileSystemStorage(location=getattr(settings, "TEST_STORAGE", None)),
        upload_to="tests",
    )
    size = models.IntegerField(default=0)
    quality = models.IntegerField(default=0)
    isBinary = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        # This variable can hold the testcase data temporarily
        self.content = None

        # For performance reasons we do not load the test here
        # automatically. You must call the loadTest method if you
        # want to access the test content

        self._original_quality = None

        super().__init__(*args, **kwargs)

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._original_quality = instance.quality
        return instance

    def loadTest(self):
        self.test.open(mode="rb")
        self.content = self.test.read()
        self.test.close()

    def storeTestAndSave(self):
        self.size = len(self.content)
        self.test.open(mode="w")
        self.test.write(self.content)
        self.test.close()
        self.save()


@receiver(post_delete, sender=TestCase)
def TestCase_delete(sender, instance, **kwargs):
    if instance.test:
        instance.test.delete(False)


@receiver(post_save, sender=TestCase)
def TestCase_save(sender, instance, created, **kwargs):
    crash = CrashEntry.objects.filter(testcase_id=instance.id).first()
    if crash and crash.bucket is not None and instance._original_quality is not None:
        BucketStatistics.update_quality(
            crash.bucket_id, crash.tool_id, instance._original_quality, instance.quality
        )


class Client(models.Model):
    name = models.CharField(max_length=255, unique=True)


class BugProvider(models.Model):
    classname = models.CharField(max_length=255, blank=False)
    hostname = models.CharField(max_length=255, blank=False)

    # This is used to annotate bugs with the URL linking to them
    urlTemplate = models.CharField(max_length=1023, blank=False)

    def getInstance(self):
        # Dynamically instantiate the provider as requested
        provider_module = __import__(
            f"crashmanager.Bugtracker.{self.classname}", fromlist=[self.classname]
        )
        provider_class = getattr(provider_module, self.classname)
        return provider_class(self.pk, self.hostname)

    def __str__(self):
        return self.hostname


class Bug(models.Model):
    externalId = models.CharField(max_length=255, blank=True)
    externalType = models.ForeignKey(BugProvider, on_delete=models.deletion.CASCADE)
    closed = models.DateTimeField(blank=True, null=True)

    @property
    def tools_filter_users(self):
        ids = User.objects.filter(
            defaultToolsFilter__crashentry__bucket__in=self.bucket_set.all(),
            inaccessible_bug=True,
        ).values_list("user_id", flat=True)
        return DjangoUser.objects.filter(id__in=ids).distinct()


class Bucket(models.Model):
    bug = models.ForeignKey(
        Bug, blank=True, null=True, on_delete=models.deletion.CASCADE
    )
    signature = models.TextField()
    optimizedSignature = models.TextField(blank=True, null=True)
    shortDescription = models.CharField(max_length=1023, blank=True)
    frequent = models.BooleanField(blank=False, default=False)
    permanent = models.BooleanField(blank=False, default=False)
    doNotReduce = models.BooleanField(blank=False, default=False)
    reassign_in_progress = models.BooleanField(default=False)

    @property
    def watchers(self):
        ids = User.objects.filter(
            bucketwatch__bucket=self, bucket_hit=True
        ).values_list("user_id", flat=True)
        return DjangoUser.objects.filter(id__in=ids).distinct()

    def getSignature(self):
        return CrashSignature(self.signature)

    def getOptimizedSignature(self):
        return CrashSignature(self.optimizedSignature)

    def save(self, *args, **kwargs):
        modified = set()

        # Sanitize signature line endings so we end up with the same hash
        # TODO: We might want to just parse the JSON here, and re-serialize
        # it to a canonical string representation.
        new_signature = self.signature.replace(r"\r\n", r"\n")
        if new_signature != self.signature:
            modified.add("signature")
            self.signature = new_signature

        # TODO: We could reset this only when we actually modify the signature,
        # but this would require fetching the old signature from the database again.
        keep_optimized = kwargs.pop("keepOptimized", False)
        if not keep_optimized:
            self.optimizedSignature = None
            modified.add("optimizedSignature")

        # required in Django 4.2+
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            kwargs["update_fields"] = modified.union(kwargs["update_fields"])

        super().save(*args, **kwargs)

    def reassign(self, submit_save, limit=None, offset=None):
        """
        Assign all unassigned issues that match our signature to this bucket.
        Furthermore, remove all non-matching issues from our bucket.

        We only actually save if "submit_save" is set.
        For previewing, we just count how many issues would be assigned and removed.
        """
        from .serializers import CrashEntryVueSerializer

        in_list, out_list = [], []
        in_list_count, out_list_count = 0, 0

        signature = self.getSignature()
        need_test = signature.matchRequiresTest()
        entries = CrashEntry.objects.filter(
            models.Q(bucket=None) | models.Q(bucket=self)
        )
        entries = entries.select_related(
            "product", "platform", "os"
        )  # these are used by getCrashInfo
        if need_test:
            entries = entries.select_related("testcase")

        required_outputs = signature.getRequiredOutputSources()
        entries = CrashEntry.deferRawFields(entries, required_outputs)

        # ensure a consistent sort otherwise not all crashes will be visited
        # - sort descending for preview for aesthetics
        # - sort ascending for save so incoming crashes aren't missed
        if not submit_save:
            entries = entries.select_related("tool")  # used by the preview list
            entries = entries.order_by("-id")
        else:
            entries = entries.order_by("id")

        # implement limit/offset pagination of reassignment to support
        # batched requests from frontend
        if limit is not None:
            assert limit > 0
            assert offset is None or offset >= 0
        else:
            assert offset is None

        entry_ids = entries.values_list("id", flat=True)
        if offset:
            entry_ids = entry_ids[offset:]

        next_offset = None
        if limit:
            remainder = entry_ids.count()
            if remainder > limit:
                next_offset = (offset or 0) + limit
            entry_ids = entry_ids[:limit]

        def grouper(iterable, n):
            """Collect data into fixed-length chunks or blocks"""
            # grouper('ABCDEFG', 3) --> ABC DEF G
            while iterable:
                result, iterable = iterable[:n], iterable[n:]
                yield result

        # If we are saving, we only care about the id of each entry
        # Otherwise, we save the entire object. Limit to the first 100 entries to avoid
        # OOM.
        for entry_ids_chunk in grouper(entry_ids, 100):
            entries_chunk = entries.filter(id__in=entry_ids_chunk)

            for entry in entries_chunk:
                match = signature.matches(
                    entry.getCrashInfo(
                        attachTestcase=need_test, requiredOutputSources=required_outputs
                    )
                )
                if match and entry.bucket_id is None:
                    if submit_save:
                        in_list.append(entry.pk)
                    elif len(in_list) < 100:
                        in_list.append(CrashEntryVueSerializer(entry).data)
                    in_list_count += 1
                elif not match and entry.bucket_id is not None:
                    if submit_save:
                        out_list.append(entry.pk)
                    elif len(out_list) < 100:
                        out_list.append(CrashEntryVueSerializer(entry).data)
                    out_list_count += 1

        if submit_save:
            for upd_list in grouper(in_list, 500):
                for crash in CrashEntry.objects.filter(pk__in=upd_list).values(
                    "bucket_id", "created", "tool_id", "testcase__quality"
                ):
                    if crash["bucket_id"] != self.id:
                        if crash["bucket_id"] is not None:
                            BucketHit.decrement_count(
                                crash["bucket_id"], crash["tool_id"], crash["created"]
                            )
                            BucketStatistics.decrement_count(
                                crash["bucket_id"],
                                crash["tool_id"],
                                crash["testcase__quality"],
                            )
                        BucketHit.increment_count(
                            self.id, crash["tool_id"], crash["created"]
                        )
                        BucketStatistics.increment_count(
                            self.id, crash["tool_id"], crash["testcase__quality"]
                        )
                CrashEntry.objects.filter(pk__in=upd_list).update(
                    bucket=self, triagedOnce=True
                )
            for upd_list in grouper(out_list, 500):
                for crash in CrashEntry.objects.filter(pk__in=upd_list).values(
                    "bucket_id", "created", "tool_id", "testcase__quality"
                ):
                    if crash["bucket_id"] is not None:
                        BucketHit.decrement_count(
                            crash["bucket_id"], crash["tool_id"], crash["created"]
                        )
                        BucketStatistics.decrement_count(
                            crash["bucket_id"],
                            crash["tool_id"],
                            crash["testcase__quality"],
                        )
                CrashEntry.objects.filter(pk__in=upd_list).update(
                    bucket=None, triagedOnce=False
                )
                if getattr(settings, "USE_CELERY", None):
                    for crash_id in upd_list:
                        triage_new_crash.delay(crash_id)

        return in_list, out_list, in_list_count, out_list_count, next_offset

    def optimizeSignature(self, unbucketed_entries):
        buckets = Bucket.objects.all()

        signature = self.getSignature()
        if signature.matchRequiresTest():
            unbucketed_entries.select_related("testcase")

        required_outputs = signature.getRequiredOutputSources()
        entries = CrashEntry.deferRawFields(unbucketed_entries, required_outputs)

        optimized_signature = None
        matching_entries = []

        # Avoid hitting the database multiple times when looking for the first
        # entry of a bucket. Keeping these in memory is less expensive.
        first_entry_per_bucket_cache = {}

        for entry in entries:
            entry.crashinfo = entry.getCrashInfo(
                attachTestcase=signature.matchRequiresTest(),
                requiredOutputSources=required_outputs,
            )

            # For optimization, disregard any issues that directly match since those
            # could be incoming new issues and we don't want these to block the
            # optimization.
            if signature.matches(entry.crashinfo):
                continue

            optimized_signature = signature.fit(entry.crashinfo)
            if optimized_signature:
                # We now try to determine how this signature will behave in other
                # buckets. If the signature matches lots of other buckets as well, it is
                # likely too broad and we should not consider it (or later rate it worse
                # than others).
                matches_in_other_buckets = False
                non_matches_in_other_buckets = 0  # noqa
                other_matching_bucket_ids = []  # noqa
                for other_bucket in buckets:
                    if other_bucket.pk == self.pk:
                        continue

                    if (
                        self.bug
                        and other_bucket.bug
                        and self.bug.pk == other_bucket.bug.pk
                    ):
                        # Allow matches in other buckets if they are both linked to the
                        # same bug
                        continue

                    if other_bucket.pk not in first_entry_per_bucket_cache:
                        c = CrashEntry.objects.filter(
                            bucket=other_bucket
                        ).select_related("product", "platform", "os")
                        c = CrashEntry.deferRawFields(c, required_outputs)
                        c = c.first()
                        first_entry_per_bucket_cache[other_bucket.pk] = c
                        if c:
                            # Omit testcase for performance reasons for now
                            first_entry_per_bucket_cache[other_bucket.pk] = (
                                c.getCrashInfo(
                                    attachTestcase=False,
                                    requiredOutputSources=required_outputs,
                                )
                            )

                    first_entry_crash_info = first_entry_per_bucket_cache[
                        other_bucket.pk
                    ]
                    if first_entry_crash_info:
                        # Omit testcase for performance reasons for now
                        if optimized_signature.matches(first_entry_crash_info):
                            matches_in_other_buckets = True
                            break

                if matches_in_other_buckets:
                    # Reset, we don't actually have an optimized signature if it's
                    # matching some other bucket as well.
                    optimized_signature = None
                else:
                    for otherEntry in entries:
                        otherEntry.crashinfo = otherEntry.getCrashInfo(
                            attachTestcase=False, requiredOutputSources=required_outputs
                        )
                        if optimized_signature.matches(otherEntry.crashinfo):
                            matching_entries.append(otherEntry)

                    # Fallback for when the optimization algorithm failed for some
                    # reason
                    if not matching_entries:
                        optimized_signature = None

                    break

        return (optimized_signature, matching_entries)


class BucketStatistics(models.Model):
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE)
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE)
    size = models.IntegerField(default=0)
    quality = models.IntegerField(null=True)

    @classmethod
    def increment_count(cls, bucket_id, tool_id, quality=None):
        stats, _ = cls.objects.get_or_create(bucket_id=bucket_id, tool_id=tool_id)
        stats.size += 1
        if quality is not None:
            if stats.quality is None or quality < stats.quality:
                stats.quality = quality
        stats.save()

    @classmethod
    def decrement_count(cls, bucket_id, tool_id, removed_quality=None):
        stats = cls.objects.filter(bucket_id=bucket_id, tool_id=tool_id).first()

        if stats and stats.size > 0:
            stats.size -= 1

            # Recalculate quality if:
            # - We still have entries (size > 0)
            # - AND the removed quality is less than or equal to the current minimum
            if stats.size > 0 and stats.quality is not None:
                if removed_quality is not None and removed_quality <= stats.quality:
                    stats.quality = CrashEntry.objects.filter(
                        bucket_id=bucket_id, tool_id=tool_id, testcase__isnull=False
                    ).aggregate(min_quality=Min("testcase__quality"))["min_quality"]
            else:
                stats.quality = None
            stats.save()

    @classmethod
    def update_quality(cls, bucket_id, tool_id, old_quality, new_quality):
        """called when a crash.testcase quality is changed"""
        stats = cls.objects.filter(bucket_id=bucket_id, tool_id=tool_id).first()

        if stats:
            if stats.quality is None or new_quality < stats.quality:
                stats.quality = new_quality
                stats.save()
            elif old_quality == stats.quality and new_quality > old_quality:
                stats.quality = CrashEntry.objects.filter(
                    bucket_id=bucket_id, tool_id=tool_id, testcase__isnull=False
                ).aggregate(min_quality=Min("testcase__quality"))["min_quality"]
                stats.save()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bucket", "tool"],
                name="unique_bucketstats_per_tool",
            ),
        ]


def buckethit_default_range_begin():
    return timezone.now().replace(microsecond=0, second=0, minute=0)


class BucketHit(models.Model):
    bucket = models.ForeignKey(Bucket, on_delete=models.deletion.CASCADE)
    tool = models.ForeignKey(Tool, on_delete=models.deletion.CASCADE)
    begin = models.DateTimeField(default=buckethit_default_range_begin)
    count = models.IntegerField(default=0)

    @classmethod
    def decrement_count(cls, bucket_id, tool_id, begin):
        begin = begin.replace(microsecond=0, second=0, minute=0)
        counter = cls.objects.filter(
            bucket_id=bucket_id,
            begin=begin,
            tool_id=tool_id,
        ).first()
        if counter is not None and counter.count > 0:
            counter.count -= 1
            counter.save()

    @classmethod
    def increment_count(cls, bucket_id, tool_id, begin):
        begin = begin.replace(microsecond=0, second=0, minute=0)
        counter, _ = cls.objects.get_or_create(
            bucket_id=bucket_id, begin=begin, tool_id=tool_id
        )
        counter.count += 1
        counter.save()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bucket", "tool", "begin"],
                name="unique_buckethits_per_period",
            ),
        ]


class CrashHit(models.Model):
    lastUpdate = models.DateTimeField(default=timezone.now)
    tool = models.ForeignKey(Tool, on_delete=models.deletion.CASCADE)
    count = models.BigIntegerField(default=0)

    @staticmethod
    def get_period(time):
        if not time.minute and not time.second and not time.microsecond:
            # we're on the hour. this is the time
            return time
        # next hour
        return time + timedelta(
            hours=1,
            minutes=-time.minute,
            seconds=-time.second,
            microseconds=-time.microsecond,
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lastUpdate", "tool"],
                name="unique_crashhits_per_tool",
            ),
        ]


class CrashEntry(models.Model):
    created = models.DateTimeField(default=timezone.now)
    tool = models.ForeignKey(Tool, on_delete=models.deletion.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.deletion.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.deletion.CASCADE)
    os = models.ForeignKey(OS, on_delete=models.deletion.CASCADE)
    testcase = models.OneToOneField(
        TestCase, blank=True, null=True, on_delete=models.deletion.CASCADE
    )
    client = models.ForeignKey(Client, on_delete=models.deletion.CASCADE)
    bucket = models.ForeignKey(
        Bucket, blank=True, null=True, on_delete=models.deletion.CASCADE
    )
    rawStdout = models.TextField(blank=True)
    rawStderr = models.TextField(blank=True)
    rawCrashData = models.TextField(blank=True)
    metadata = models.TextField(blank=True)
    env = models.TextField(blank=True)
    args = models.TextField(blank=True)
    crashAddress = models.CharField(max_length=255, blank=True)
    crashAddressNumeric = models.BigIntegerField(blank=True, null=True)
    shortSignature = models.CharField(max_length=255, blank=True)
    cachedCrashInfo = models.TextField(blank=True, null=True)
    triagedOnce = models.BooleanField(blank=False, default=False)

    def __init__(self, *args, **kwargs):
        # These variables can hold temporarily deserialized data
        self.argsList = None
        self.envList = None
        self.metadataList = None

        # For performance reasons we do not deserialize these fields
        # automatically here. You need to explicitly call the
        # deserializeFields method if you need this data.

        self._original_bucket = None
        super().__init__(*args, **kwargs)

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._original_bucket = instance.bucket_id
        return instance

    def save(self, *args, **kwargs):
        modified = set()

        if self.pk is None and not getattr(settings, "DB_ISUTF8MB4", False):
            # Replace 4-byte UTF-8 characters with U+FFFD if our database
            # doesn't support them. By default, MySQL utf-8 does not support these.
            utf8_4byte_re = re.compile("[^\u0000-\ud7ff\ue000-\uffff]", re.UNICODE)

            def sanitize_utf8(s):
                if not isinstance(s, str):
                    s = str(s, "utf-8")

                return utf8_4byte_re.sub("\ufffd", s)

            new_rawStdout = sanitize_utf8(self.rawStdout)
            if self.rawStdout != new_rawStdout:
                self.rawStdout = new_rawStdout
                modified.add("rawStdout")
            new_rawStderr = sanitize_utf8(self.rawStderr)
            if self.rawStderr != new_rawStderr:
                self.rawStderr = new_rawStderr
                modified.add("rawStderr")
            new_rawCrashData = sanitize_utf8(self.rawCrashData)
            if self.rawCrashData != new_rawCrashData:
                self.rawCrashData = new_rawCrashData
                modified.add("rawCrashData")

        if not self.cachedCrashInfo:
            # Serialize the important fields of the CrashInfo class into a JSON blob
            crashInfo = self.getCrashInfo()
            self.cachedCrashInfo = json.dumps(crashInfo.toCacheObject())
            modified.add("cachedCrashInfo")

        # Reserialize data, then call regular save method
        if self.argsList:
            new_args = json.dumps(self.argsList)
            if new_args != self.args:
                self.args = new_args
                modified.add("args")

        if self.envList:
            envDict = dict(x.split("=", 1) for x in self.envList)
            new_env = json.dumps(envDict)
            if new_env != self.env:
                self.env = new_env
                modified.add("env")

        if self.metadataList:
            metadataDict = dict(x.split("=", 1) for x in self.metadataList)
            new_metadata = json.dumps(metadataDict)
            if new_metadata != self.metadata:
                self.metadata = new_metadata
                modified.add("metadata")

        # When we have a crash address, keep the numeric crash address field in
        # sync so we can search easily by crash address including ranges
        if self.crashAddress:
            orig_crashAddressNumeric = self.crashAddressNumeric
            self.crashAddressNumeric = int(self.crashAddress, 16)

            # We need to possibly convert the numeric crash address from unsigned
            # to signed in order to store it in the database.
            if self.crashAddressNumeric > (2**63 - 1):
                self.crashAddressNumeric -= 2**64

            if orig_crashAddressNumeric != self.crashAddressNumeric:
                modified.add("crashAddressNumeric")

        if len(self.shortSignature) > 255:
            self.shortSignature = self.shortSignature[:255]
            modified.add("shortSignature")

        # required in Django 4.2+
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            kwargs["update_fields"] = modified.union(kwargs["update_fields"])

        super().save(*args, **kwargs)

    def deserializeFields(self):
        if self.args:
            self.argsList = json.loads(self.args)

        if self.env:
            envDict = json.loads(self.env)
            self.envList = [f"{s}={envDict[s]}" for s in envDict.keys()]

        if self.metadata:
            metadataDict = json.loads(self.metadata)
            self.metadataList = [f"{s}={metadataDict[s]}" for s in metadataDict.keys()]

    def getCrashInfo(
        self,
        attachTestcase=False,
        requiredOutputSources=("stdout", "stderr", "crashdata"),
    ):
        # TODO: This should be cached at some level
        # TODO: Need to include environment and program arguments here
        configuration = ProgramConfiguration(
            self.product.name, self.platform.name, self.os.name, self.product.version
        )

        cachedCrashInfo = None
        if self.cachedCrashInfo:
            cachedCrashInfo = json.loads(self.cachedCrashInfo)

        # We can skip loading raw output fields from the database iff
        #   1) we know we don't need them for matching *and*
        #   2) we already have the crash data cached
        (rawStdout, rawStderr, rawCrashData) = (None, None, None)
        if cachedCrashInfo is None or "stdout" in requiredOutputSources:
            rawStdout = self.rawStdout
        if cachedCrashInfo is None or "stderr" in requiredOutputSources:
            rawStderr = self.rawStderr
        if cachedCrashInfo is None or "crashdata" in requiredOutputSources:
            rawCrashData = self.rawCrashData

        crashInfo = CrashInfo.fromRawCrashData(
            rawStdout,
            rawStderr,
            configuration,
            rawCrashData,
            cacheObject=cachedCrashInfo,
        )

        if attachTestcase and self.testcase is not None and not self.testcase.isBinary:
            self.testcase.loadTest()
            crashInfo.testcase = self.testcase.content

        return crashInfo

    def reparseCrashInfo(self):
        # Purges cached crash information and then forces a reparsing
        # of the raw crash information. Based on the new crash information,
        # the depending fields are also repopulated.
        #
        # This method should only be called if either the raw crash information
        # has changed or the implementation parsing it was updated.
        self.cachedCrashInfo = None
        crashInfo = self.getCrashInfo()
        if crashInfo.crashAddress is not None:
            self.crashAddress = f"0x{crashInfo.crashAddress:x}"
        self.shortSignature = crashInfo.createShortSignature()

        # If the entry has a bucket, check if it still fits into
        # this bucket, otherwise remove it.
        if self.bucket is not None:
            sig = self.bucket.getSignature()
            crashInfo = self.getCrashInfo(attachTestcase=sig.matchRequiresTest())
            if not sig.matches(crashInfo):
                self.bucket = None

        # If this entry now isn't in a bucket, mark it to be auto-triaged
        # again by the server.
        if self.bucket is None:
            self.triagedOnce = False

        return self.save()

    @staticmethod
    def deferRawFields(queryset, requiredOutputSources=()):
        # This method calls defer() on the given query set for every raw field
        # that is not required as specified in requiredOutputSources.
        if "stdout" not in requiredOutputSources:
            queryset = queryset.defer("rawStdout")
        if "stderr" not in requiredOutputSources:
            queryset = queryset.defer("rawStderr")
        if "crashdata" not in requiredOutputSources:
            queryset = queryset.defer("rawCrashData")
        return queryset


# These post_delete handlers ensure that the corresponding testcase
# is also deleted when the CrashEntry is gone. It also explicitly
# deletes the file on the filesystem which would otherwise remain.
@receiver(post_delete, sender=CrashEntry)
def CrashEntry_delete(sender, instance, **kwargs):
    if instance.testcase:
        instance.testcase.delete(False)
    if instance.bucket_id is not None:
        BucketHit.decrement_count(
            instance.bucket_id, instance.tool_id, instance.created
        )
        BucketStatistics.decrement_count(
            instance.bucket_id,
            instance.tool_id,
            instance.testcase.quality if instance.testcase else None,
        )


@receiver(post_save, sender=CrashEntry)
def CrashEntry_save(sender, instance, created, **kwargs):
    if getattr(settings, "USE_CELERY", None):
        # this could mean the crash is new, or that it was edited and reparsed
        if not instance.triagedOnce:
            triage_new_crash.delay(instance.pk)

    if instance.bucket_id != instance._original_bucket:
        if instance._original_bucket is not None:
            # remove BucketHit for old bucket/tool
            BucketHit.decrement_count(
                instance._original_bucket, instance.tool_id, instance.created
            )
            # remove BucketStatistics for old bucket
            BucketStatistics.decrement_count(
                instance._original_bucket,
                instance.tool_id,
                instance.testcase.quality if instance.testcase else None,
            )

        if instance.bucket is not None:
            # add BucketHit for new bucket
            BucketHit.increment_count(
                instance.bucket_id, instance.tool_id, instance.created
            )
            # add BucketStatistics for new bucket
            quality = instance.testcase.quality if instance.testcase else None
            BucketStatistics.increment_count(
                instance.bucket_id, instance.tool_id, quality
            )

        if instance.bucket is not None:
            notify.send(
                instance.bucket,
                recipient=instance.bucket.watchers,
                actor=instance.bucket,
                verb="bucket_hit",
                target=instance,
                level="info",
                description=(
                    f"The bucket {instance.bucket_id} received a new crash entry "
                    f"{instance.pk}"
                ),
            )


class BugzillaTemplateMode(Enum):
    Bug = "bug"
    Comment = "comment"


class BugzillaTemplate(models.Model):
    mode = EnumField(BugzillaTemplateMode, max_length=30)
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
    testcase_filename = models.TextField(blank=True)
    blocks = models.TextField(blank=True)
    dependson = models.TextField(blank=True)

    def __str__(self):
        return self.name


class User(models.Model):
    class Meta:
        permissions = (
            (
                "view_crashmanager",
                "Can see CrashManager app (required for crashmanager_* perms)",
            ),
            (
                "view_covmanager",
                "Can see CovManager app (required for covmanager_* perms",
            ),
            (
                "view_ec2spotmanager",
                "Can see EC2SpotManager app (required for ec2spotmanager_* perms)",
            ),
            (
                "view_taskmanager",
                "Can see TaskManager app (required for taskmanager_* perms)",
            ),
            ("crashmanager_report_crashes", "Can report CrashManager crashes"),
            ("crashmanager_download_signatures", "Can download signatures.zip"),
            ("crashmanager_all", "Full access to CrashManager"),
            ("covmanager_submit_collection", "Can submit coverage data"),
            ("covmanager_publish", "Can publish coverage reports"),
            ("covmanager_all", "Full access to CovManager"),
            ("taskmanager_report_status", "Can report TaskManager status"),
            ("taskmanager_all", "Full access to TaskManager"),
            ("ec2spotmanager_report_status", "Can report EC2SpotManager status"),
            ("ec2spotmanager_all", "Full access to EC2SpotManager"),
        )

    user = models.OneToOneField(DjangoUser, on_delete=models.deletion.CASCADE)
    # Explicitly do not store this as a ForeignKey to e.g. BugzillaTemplate
    # because the bug provider has to decide how to interpret this ID.
    defaultTemplateId = models.IntegerField(default=0)
    defaultProviderId = models.IntegerField(default=1)
    defaultToolsFilter = models.ManyToManyField(Tool)
    restricted = models.BooleanField(blank=False, default=False)
    bucketsWatching = models.ManyToManyField(Bucket, through="BucketWatch")

    # Notifications
    bucket_hit = models.BooleanField(blank=False, default=False)
    coverage_drop = models.BooleanField(blank=False, default=False)
    inaccessible_bug = models.BooleanField(blank=False, default=False)
    tasks_failed = models.BooleanField(blank=False, default=False)

    @staticmethod
    def get_or_create_restricted(request_user):
        (user, created) = User.objects.get_or_create(user=request_user)
        if created and getattr(settings, "USERS_RESTRICTED_BY_DEFAULT", False):
            user.restricted = True
            user.save()
        return (user, created)


@receiver(post_save, sender=DjangoUser)
def add_default_perms(sender, instance, created, **kwargs):
    if created:
        for perm in getattr(settings, "DEFAULT_PERMISSIONS", []):
            model, perm = perm.split(":", 1)
            module, model = model.rsplit(".", 1)
            module = __import__(
                module, globals(), locals(), [model], 0
            )  # from module import model
            content_type = ContentType.objects.get_for_model(getattr(module, model))
            perm = Permission.objects.get(content_type=content_type, codename=perm)
            instance.user_permissions.add(perm)
            LOG.info("user %s added permission %s:%s", instance.username, model, perm)


class BucketWatch(models.Model):
    user = models.ForeignKey(User, on_delete=models.deletion.CASCADE)
    bucket = models.ForeignKey(Bucket, on_delete=models.deletion.CASCADE)
    # This is the primary key of last crash marked viewed by the user
    # Store as an integer to prevent problems if the particular crash
    # is deleted later. We only care about its place in the ordering.
    lastCrash = models.IntegerField(default=0)
