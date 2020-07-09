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
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.deletion.CASCADE)
    name = models.CharField(max_length=255, blank=False)
    size = models.IntegerField(default=1, blank=True, null=True)
    cycle_interval = models.IntegerField(default=86400, blank=True, null=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True)
    instance_tags = models.CharField(max_length=1023, blank=True, null=True)
    ec2_key_name = models.CharField(max_length=255, blank=True, null=True)
    ec2_security_groups = models.CharField(max_length=255, blank=True, null=True)
    ec2_instance_types = models.CharField(max_length=4095, blank=True, null=True)
    ec2_image_name = models.CharField(max_length=255, blank=True, null=True)
    ec2_userdata_file = \
        models.FileField(storage=OverwritingStorage(location=getattr(settings, 'USERDATA_STORAGE', None)),
                         upload_to=get_storage_path, blank=True, null=True)
    ec2_userdata_macros = models.CharField(max_length=4095, blank=True, null=True)
    ec2_allowed_regions = models.CharField(max_length=1023, blank=True, null=True)
    ec2_raw_config = models.CharField(max_length=4095, blank=True, null=True)
    gce_machine_types = models.CharField(max_length=4095, blank=True, null=True)
    gce_image_name = models.CharField(max_length=255, blank=True, null=True)
    gce_container_name = models.CharField(max_length=512, blank=True, null=True)
    gce_docker_privileged = models.BooleanField(default=False)
    gce_disk_size = models.IntegerField(blank=True, null=True)
    gce_cmd = models.CharField(max_length=4095, blank=True, null=True)
    gce_args = models.CharField(max_length=4095, blank=True, null=True)
    gce_env = models.CharField(max_length=4095, blank=True, null=True)
    # this is a special case that allows copying ec2_userdata_macros into gce_env during flatten()
    # we typically use userdata_macros to be the env vars provided to the userdata script
    gce_env_include_macros = models.BooleanField(default=False)
    gce_raw_config = models.CharField(max_length=4095, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        # These variables can hold temporarily deserialized data
        self.instance_tags_dict = None
        self.instance_tags_override = None
        self.ec2_raw_config_dict = None
        self.ec2_raw_config_override = None
        self.ec2_userdata_macros_dict = None
        self.ec2_userdata_macros_override = None
        self.ec2_userdata = None
        self.ec2_security_groups_list = None
        self.ec2_security_groups_override = None
        self.ec2_allowed_regions_list = None
        self.ec2_allowed_regions_override = None
        self.ec2_instance_types_list = None
        self.ec2_instance_types_override = None
        self.gce_machine_types_list = None
        self.gce_machine_types_override = None
        self.gce_cmd_list = None
        self.gce_cmd_override = None
        self.gce_args_list = None
        self.gce_args_override = None
        self.gce_env_dict = None
        self.gce_env_override = None
        self.gce_raw_config_dict = None
        self.gce_raw_config_override = None

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
            'max_price',
            'ec2_key_name',
            'ec2_image_name',
            'ec2_userdata',
            'gce_image_name',
            'gce_container_name',
            'gce_disk_size',
            'gce_env_include_macros',
            'gce_docker_privileged',
        ]

        # Boolean fields are special in that they can be False and still be valid, though they are required.
        self.boolean_fields = [
            'gce_env_include_macros',
            'gce_docker_privileged',
        ]

        self.list_config_fields = [
            'ec2_security_groups',
            'ec2_allowed_regions',
            'ec2_instance_types',
            'gce_machine_types',
            'gce_cmd',
            'gce_args',
        ]

        self.dict_config_fields = [
            'instance_tags',
            'ec2_raw_config',
            'ec2_userdata_macros',
            'gce_env',
            'gce_raw_config',
        ]

        # For performance reasons we do not deserialize these fields
        # automatically here. You need to explicitly call the
        # deserializeFields method if you need this data.

        super(PoolConfiguration, self).__init__(*args, **kwargs)

    def flatten(self, cache=None):
        # cache is optionally a prefetched {config_id: config} dictionary used for parent lookups
        if self.isCyclic(cache):
            raise RuntimeError("Attempted to flatten a cyclic configuration")

        self.deserializeFields()

        # If we are not the top-most configuration, recursively call flatten
        # and proceed with the configuration provided by our parent.
        if self._cache_parent(cache) is not None:
            flat_parent_config = self._cache_parent(cache).flatten(cache)

        else:
            # Start with an empty configuration
            flat_parent_config = FlatObject({})

            # Dictionaries and lists should be explicitly initialized empty
            # so they can be updated/extended by the child configurations
            for field in self.dict_config_fields:
                flat_parent_config[field] = {}

            for field in self.list_config_fields:
                flat_parent_config[field] = []

        for config_field in self.config_fields:
            if getattr(self, config_field) is not None:
                flat_parent_config[config_field] = getattr(self, config_field)

        for field in self.dict_config_fields:
            if field == "gce_env" and self.gce_env_include_macros:
                # handle gce_env specially if gce_env_include_macros
                continue
            obj = getattr(self, field + "_dict")
            override = getattr(self, field + "_override")
            if obj and not override:
                flat_parent_config[field].update(obj)
            elif obj and override:
                flat_parent_config[field] = obj
            elif override:
                flat_parent_config[field] = {}

        # special flag to include macros in GCE environment
        # this is done after the loop to guarantee that userdata_macros have been flattened
        if self.gce_env_include_macros:
            field = "gce_env"
            gce_env = getattr(self, field + "_dict")
            override = getattr(self, field + "_override")
            # start with userdata_macros
            obj = flat_parent_config.ec2_userdata_macros.copy()
            # overlay gce_env
            if gce_env:
                obj.update(gce_env)
            # now apply same override logic as other fields
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

        if self.ec2_userdata_file:
            self.ec2_userdata_file.open(mode='rb')
            self.ec2_userdata = self.ec2_userdata_file.read()
            self.ec2_userdata_file.close()

    def storeTestAndSave(self):
        if self.ec2_userdata:
            # Save the file using save() to avoid problems when initially
            # creating the directory. We use os.path.split to keep the
            # original filename assigned when saving the file.
            self.ec2_userdata_file.save(os.path.split(self.ec2_userdata_file.name)[-1],
                                        ContentFile(self.ec2_userdata), save=False)
        elif self.ec2_userdata_file:
            self.ec2_userdata_file.delete()
            self.ec2_userdata_file = None

        self.save()

    def _cache_parent(self, cache):
        # use a prefetched {config_id: config} cache dictionary
        # to lookup self.parent
        if cache is None:
            return self.parent
        return cache.get(self.parent_id)

    def isCyclic(self, cache=None):
        # cache is optionally a prefetched {config_id: config} dictionary used for parent lookups
        if self._cache_parent(cache) is None:
            return False
        tortoise = self
        hare = self._cache_parent(cache)
        while tortoise != hare:
            if hare._cache_parent(cache) is None or hare._cache_parent(cache)._cache_parent(cache) is None:
                break
            tortoise = tortoise._cache_parent(cache)
            hare = hare._cache_parent(cache)._cache_parent(cache)
        return tortoise == hare

    def getMissingParameters(self):
        flat_config = self.flatten()
        ec2_missing_fields = []
        gce_missing_fields = []
        missing_fields = []

        # Check regular fields, none of them is optional
        for field in self.config_fields:
            if field in self.boolean_fields:
                continue
            if field not in flat_config or not flat_config[field]:
                if field.startswith("ec2_"):
                    ec2_missing_fields.append(field)
                elif field.startswith("gce_"):
                    gce_missing_fields.append(field)
                else:
                    missing_fields.append(field)

        # Most dicts/lists are optional except for the ec2_allowed_regions
        # field. Without that, we obviously cannot spawn any instances, so
        # we should report this field if it's missing or empty.
        if not flat_config.ec2_allowed_regions:
            ec2_missing_fields.append("ec2_allowed_regions")
        if not flat_config.ec2_instance_types:
            ec2_missing_fields.append("ec2_instance_types")
        if not flat_config.gce_machine_types:
            gce_missing_fields.append("gce_machine_types")

        # if either ec2 or gce are complete, consider the config complete
        if not gce_missing_fields or not ec2_missing_fields:
            return missing_fields

        return missing_fields + ec2_missing_fields + gce_missing_fields


@receiver(models.signals.post_delete, sender=PoolConfiguration)
def deletePoolConfigurationFiles(sender, instance, **kwargs):
    if instance.ec2_userdata:
        filename = instance.file.path
        filedir = os.path.dirname(filename)

        os.remove(filename)

        if not os.listdir(filedir):
            os.rmdir(filedir)


class InstancePool(models.Model):
    config = models.ForeignKey(PoolConfiguration, on_delete=models.deletion.CASCADE)
    isEnabled = models.BooleanField(default=False)
    last_cycled = models.DateTimeField(blank=True, null=True)


class Instance(models.Model):
    created = models.DateTimeField(default=timezone.now)
    pool = models.ForeignKey(InstancePool, blank=True, null=True, on_delete=models.deletion.CASCADE)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    status_code = models.IntegerField()
    status_data = models.CharField(max_length=4095, blank=True, null=True)
    instance_id = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255)
    zone = models.CharField(max_length=255)
    size = models.IntegerField(default=1)
    provider = models.CharField(max_length=255)


class InstanceStatusEntry(models.Model):
    instance = models.ForeignKey(Instance, on_delete=models.deletion.CASCADE)
    created = models.DateTimeField(default=timezone.now)
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)


class PoolStatusEntry(models.Model):
    pool = models.ForeignKey(InstancePool, on_delete=models.deletion.CASCADE)
    created = models.DateTimeField(default=timezone.now)
    type = models.IntegerField()
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)


class ProviderStatusEntry(models.Model):
    provider = models.CharField(max_length=255)
    created = models.DateTimeField(default=timezone.now)
    type = models.IntegerField()
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)


class PoolUptimeDetailedEntry(models.Model):
    pool = models.ForeignKey(InstancePool, on_delete=models.deletion.CASCADE)
    created = models.DateTimeField(default=timezone.now)
    target = models.IntegerField()
    actual = models.IntegerField()


class PoolUptimeAccumulatedEntry(models.Model):
    pool = models.ForeignKey(InstancePool, on_delete=models.deletion.CASCADE)
    created = models.DateTimeField(default=timezone.now)
    accumulated_count = models.IntegerField(default=0)
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
