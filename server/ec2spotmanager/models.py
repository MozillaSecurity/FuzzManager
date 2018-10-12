import json
import os
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.dispatch.dispatcher import receiver
from django.utils import timezone


def get_storage_path(self, name):
    return os.path.join("poolconfig-%s-files" % self.pk, name)


class FlatObject(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


POOL_STATUS_ENTRY_TYPE_CODE = {0: "unclassified", 1: "price-too-low", 2: "config-error",
                               3: "max-spot-instance-count-exceeded", 4: "temporary-failure"}
POOL_STATUS_ENTRY_TYPE = dict((val, key) for key, val in POOL_STATUS_ENTRY_TYPE_CODE.items())


class OverwritingStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(getattr(settings, 'USERDATA_STORAGE', None), name))
        return name


class PoolConfiguration(models.Model):
    parent = models.ForeignKey('self', blank=True, null=True)
    name = models.CharField(max_length=255, blank=False)
    size = models.IntegerField(default=1, blank=True, null=True)
    cycle_interval = models.IntegerField(default=86400, blank=True, null=True)
    ec2_key_name = models.CharField(max_length=255, blank=True, null=True)
    ec2_security_groups = models.CharField(max_length=255, blank=True, null=True)
    ec2_instance_types = models.CharField(max_length=4095, blank=True, null=True)
    ec2_image_name = models.CharField(max_length=255, blank=True, null=True)
    userdata_file = models.FileField(storage=OverwritingStorage(location=getattr(settings, 'USERDATA_STORAGE', None)),
                                     upload_to=get_storage_path, blank=True, null=True)
    userdata_macros = models.CharField(max_length=4095, blank=True, null=True)
    ec2_allowed_regions = models.CharField(max_length=1023, blank=True, null=True)
    ec2_max_price = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True)
    ec2_tags = models.CharField(max_length=1023, blank=True, null=True)
    ec2_raw_config = models.CharField(max_length=4095, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        # These variables can hold temporarily deserialized data
        self.ec2_tags_dict = None
        self.ec2_tags_override = None
        self.ec2_raw_config_dict = None
        self.ec2_raw_config_override = None
        self.userdata_macros_dict = None
        self.userdata_macros_override = None
        self.userdata = None
        self.ec2_security_groups_list = None
        self.ec2_security_groups_override = None
        self.ec2_allowed_regions_list = None
        self.ec2_allowed_regions_override = None
        self.ec2_instance_types_list = None
        self.ec2_instance_types_override = None

        # This list is used to update the parent configuration with our own
        # values and to check for missing fields in our flat config.
        #
        # All fields of our model except for the parent and name
        # fields are inheritable and follow the precedence model.
        #
        # The fields which are dictionaries/lists get special treatment
        # because they should behave in an additive manner.
        self.config_fields = [
            'size',
            'cycle_interval',
            'ec2_key_name',
            'ec2_image_name',
            'ec2_max_price',
            'userdata',
        ]

        self.list_config_fields = [
            'ec2_security_groups',
            'ec2_allowed_regions',
            'ec2_instance_types',
        ]

        self.dict_config_fields = [
            'ec2_tags',
            'ec2_raw_config',
            'userdata_macros',
        ]

        # For performance reasons we do not deserialize these fields
        # automatically here. You need to explicitly call the
        # deserializeFields method if you need this data.

        super(PoolConfiguration, self).__init__(*args, **kwargs)

    def flatten(self):
        if self.isCyclic():
            raise RuntimeError("Attempted to flatten a cyclic configuration")

        self.deserializeFields()

        # Start with an empty configuration
        flat_parent_config = FlatObject({})

        # Dictionaries and lists should be explicitely initialized empty
        # so they can be updated/extended by the child configurations
        for field in self.dict_config_fields:
            flat_parent_config[field] = {}

        for field in self.list_config_fields:
            flat_parent_config[field] = []

        # If we are not the top-most confifugration, recursively call flatten
        # and proceed with the configuration provided by our parent.
        if self.parent is not None:
            flat_parent_config = self.parent.flatten()

        for config_field in self.config_fields:
            if getattr(self, config_field) is not None:
                flat_parent_config[config_field] = getattr(self, config_field)

        for field in self.dict_config_fields:
            obj = getattr(self, field + "_dict")
            override = getattr(self, field + "_override")
            if obj and not override:
                flat_parent_config[field].update(obj)
            elif obj and override:
                flat_parent_config[field] = obj
            elif override:
                flat_parent_config[field] = {}

        for field in self.list_config_fields:
            obj = getattr(self, field + "_list")
            override = getattr(self, field + "_override")
            if obj and not override:
                flat_parent_config[field].extend(obj)
            elif obj and override:
                flat_parent_config[field] = obj
            elif override:
                flat_parent_config[field] = []

        return flat_parent_config

    def save(self, *args, **kwargs):
        # Reserialize data, then call regular save method
        for field in self.dict_config_fields:
            obj = getattr(self, field + "_dict")
            override = getattr(self, field + "_override")
            if obj:
                value = json.dumps(obj, separators=(',', ':'))
            else:
                value = ''
            if override:
                value = '!' + value
            setattr(self, field, value)

        for field in self.list_config_fields:
            obj = getattr(self, field + "_list")
            override = getattr(self, field + "_override")
            if obj:
                value = json.dumps(obj, separators=(',', ':'))
            else:
                value = ''
            if override:
                value = '!' + value
            setattr(self, field, value)

        super(PoolConfiguration, self).save(*args, **kwargs)

    def deserializeFields(self):
        for field in self.dict_config_fields:
            sobj = getattr(self, field) or ''
            setattr(self, field + '_override', sobj.startswith('!'))
            sobj = sobj.lstrip('!')
            if sobj:
                setattr(self, field + '_dict', json.loads(sobj))

        for field in self.list_config_fields:
            sobj = getattr(self, field) or ''
            setattr(self, field + '_override', sobj.startswith('!'))
            sobj = sobj.lstrip('!')
            if sobj:
                setattr(self, field + '_list', json.loads(sobj))

        if self.userdata_file:
            self.userdata_file.open(mode='rb')
            self.userdata = self.userdata_file.read()
            self.userdata_file.close()

    def storeTestAndSave(self):
        if self.userdata:
            # Save the file using save() to avoid problems when initially
            # creating the directory. We use os.path.split to keep the
            # original filename assigned when saving the file.
            self.userdata_file.save(os.path.split(self.userdata_file.name)[-1],
                                    ContentFile(self.userdata), save=False)
        elif self.userdata_file:
            self.userdata_file.delete()
            self.userdata_file = None

        self.save()

    def isCyclic(self):
        if not self.parent:
            return False
        tortoise = self
        hare = self.parent
        while tortoise != hare and hare.parent and hare.parent.parent:
            tortoise = tortoise.parent
            hare = hare.parent.parent
        return tortoise == hare

    def getMissingParameters(self):
        flat_config = self.flatten()
        missing_fields = []

        # Check regular fields, none of them is optional
        for field in self.config_fields:
            if field not in flat_config or not flat_config[field]:
                missing_fields.append(field)

        # Most dicts/lists are optional except for the ec2_allowed_regions
        # field. Without that, we obviously cannot spawn any instances, so
        # we should report this field if it's missing or empty.
        if not flat_config.ec2_allowed_regions:
            missing_fields.append("ec2_allowed_regions")

        return missing_fields


@receiver(models.signals.post_delete, sender=PoolConfiguration)
def deletePoolConfigurationFiles(sender, instance, **kwargs):
    if instance.userdata:
        filename = instance.file.path
        filedir = os.path.dirname(filename)

        os.remove(filename)

        if not os.listdir(filedir):
            os.rmdir(filedir)


class InstancePool(models.Model):
    config = models.ForeignKey(PoolConfiguration)
    isEnabled = models.BooleanField(default=False)
    last_cycled = models.DateTimeField(blank=True, null=True)


class Instance(models.Model):
    created = models.DateTimeField(default=timezone.now)
    pool = models.ForeignKey(InstancePool, blank=True, null=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    status_code = models.IntegerField()
    status_data = models.CharField(max_length=4095, blank=True, null=True)
    instance_id = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255)
    zone = models.CharField(max_length=255)
    size = models.IntegerField(default=1)


class InstanceStatusEntry(models.Model):
    instance = models.ForeignKey(Instance)
    created = models.DateTimeField(default=timezone.now)
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)


class PoolStatusEntry(models.Model):
    pool = models.ForeignKey(InstancePool)
    created = models.DateTimeField(default=timezone.now)
    type = models.IntegerField()
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)


class PoolUptimeDetailedEntry(models.Model):
    pool = models.ForeignKey(InstancePool)
    created = models.DateTimeField(default=timezone.now)
    target = models.IntegerField()
    actual = models.IntegerField()


class PoolUptimeAccumulatedEntry(models.Model):
    pool = models.ForeignKey(InstancePool)
    created = models.DateTimeField(default=timezone.now)
    accumulated_count = models.IntegerField(default=0)
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
