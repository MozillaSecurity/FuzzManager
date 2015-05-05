from django.db import models
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import re
import json
import os

def get_storage_path(self, name):
    return os.path.join(re.sub("[^a-zA-Z0-9-_]", "", self.name), name)

class FlatObject(dict): 
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

INSTANCE_STATE_CODE = { 0 : "pending", 16 : "running", 32 : "shutting-down", 48 : "terminated", 64 : "stopping", 80 : "stopped" }
INSTANCE_STATE = dict((val, key) for key, val in INSTANCE_STATE_CODE.iteritems())

class PoolConfiguration(models.Model):
    parent = models.ForeignKey("self", blank=True, null=True)
    name = models.CharField(max_length=255, blank=False)
    size = models.IntegerField(default=1, blank=True, null=True)
    cycle_interval = models.IntegerField(default=86400, blank=True, null=True)
    aws_access_key_id = models.CharField(max_length=255, blank=True, null=True)
    aws_secret_access_key = models.CharField(max_length=255, blank=True, null=True)
    ec2_key_name = models.CharField(max_length=255, blank=True, null=True)
    ec2_security_groups = models.CharField(max_length=255, blank=True, null=True)
    ec2_instance_type = models.CharField(max_length=255, blank=True, null=True)
    ec2_image_name = models.CharField(max_length=255, blank=True, null=True)
    ec2_userdata_file =  models.FileField(storage=FileSystemStorage(location=getattr(settings, 'USERDATA_STORAGE', None)), upload_to=get_storage_path, blank=True, null=True)
    ec2_userdata_macros = models.CharField(max_length=4095, blank=True, null=True)
    ec2_allowed_regions = models.CharField(max_length=1023, blank=True, null=True)
    ec2_max_price = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True)
    ec2_tags = models.CharField(max_length=1023, blank=True, null=True)
    ec2_raw_config = models.CharField(max_length=4095, blank=True, null=True)
    
    def __init__(self, *args, **kwargs):
        # These variables can hold temporarily deserialized data
        self.ec2_tags_dict = None
        self.ec2_raw_config_dict = None
        self.ec2_userdata_macros_dict = None
        self.ec2_userdata = None
        self.ec2_security_groups_list = None
        self.ec2_allowed_regions_list = None
        
        # For performance reasons we do not deserialize these fields
        # automatically here. You need to explicitly call the 
        # deserializeFields method if you need this data.
        
        super(PoolConfiguration, self).__init__(*args, **kwargs)
    
    def flatten(self):
        self.deserializeFields()
        
        # Start with an empty configuration
        #
        # ec2_tags and ec2_raw_config should explicitely be initialized
        # to empty dictionaries so they can be updated later on.
        flat_parent_config = FlatObject({})
        flat_parent_config.ec2_tags = {}
        flat_parent_config.ec2_raw_config = {}
        flat_parent_config.ec2_userdata_macros = {}
        flat_parent_config.ec2_security_groups = []
        flat_parent_config.ec2_allowed_regions = []
        
        # If we are not the top-most confifugration, recursively call flatten
        # and proceed with the configuration provided by our parent.
        if self.parent != None:
            flat_parent_config = self.parent.flatten()
        
        # Now update the parent configuration with our own values
        # All fields of our model except for the parent and name
        # fields are inheritable and follow the precedence model.
        #
        # The fields which are dictionaries/lists get special treatment
        # because they should behave in an additive manner.
        config_fields = [
                         'size',
                         'aws_access_key_id',
                         'aws_secret_access_key',
                         'cycle_interval',
                         'ec2_key_name',
                         'ec2_image_name',
                         'ec2_instance_type',
                         'ec2_max_price',
                         'ec2_userdata',
                         ]
        
        for config_field in config_fields:
            if getattr(self, config_field) != None:
                flat_parent_config[config_field] = getattr(self, config_field)
                
        if self.ec2_tags_dict:
            flat_parent_config.ec2_tags.update(self.ec2_tags_dict)
            
        if self.ec2_raw_config_dict:
            flat_parent_config.ec2_raw_config.update(self.ec2_raw_config_dict)
        
        if self.ec2_userdata_macros_dict:
            flat_parent_config.ec2_userdata_macros.update(self.ec2_userdata_macros_dict)
            
        if self.ec2_security_groups_list:
            flat_parent_config.ec2_security_groups.extend(self.ec2_security_groups_list)
        
        if self.ec2_allowed_regions_list:
            flat_parent_config.ec2_allowed_regions.extend(self.ec2_allowed_regions_list)
            
        return flat_parent_config
        
    def save(self, *args, **kwargs):
        # Reserialize data, then call regular save method
        if self.ec2_tags_dict:
            self.ec2_tags = json.dumps(self.ec2_tags_dict)
    
        if self.ec2_raw_config_dict:
            self.ec2_raw_config = json.dumps(self.ec2_raw_config_dict)
            
        if self.ec2_userdata_macros_dict:
            self.ec2_userdata_macros = json.dumps(self.ec2_userdata_macros_dict)
            
        if self.ec2_security_groups_list:
            self.ec2_security_groups = json.dumps(self.ec2_security_groups_list)
        
        if self.ec2_allowed_regions_list:
            self.ec2_allowed_regions = json.dumps(self.ec2_allowed_regions_list)
                
        super(PoolConfiguration, self).save(*args, **kwargs)
    
    def deserializeFields(self):
        if self.ec2_tags:
            self.ec2_tags_dict = json.loads(self.ec2_tags)
            
        if self.ec2_raw_config:
            self.ec2_raw_config_dict = json.loads(self.ec2_raw_config)
        
        if self.ec2_userdata_macros:
            self.ec2_userdata_macros_dict = json.loads(self.ec2_userdata_macros)
            
        if self.ec2_userdata_file:
            self.ec2_userdata_file.open(mode='rb')
            self.ec2_userdata = self.ec2_userdata_file.read()
            self.ec2_userdata_file.close()
            
        if self.ec2_security_groups:
            self.ec2_security_groups_list = json.loads(self.ec2_security_groups)
            
        if self.ec2_allowed_regions:
            self.ec2_allowed_regions_list = json.loads(self.ec2_allowed_regions)
        
    def storeTestAndSave(self):
        if self.ec2_userdata:
            self.ec2_userdata_file.open(mode='w')
            self.ec2_userdata_file.write(self.ec2_userdata)
            self.ec2_userdata_file.close()
            self.save()
    
class InstancePool(models.Model):
    config = models.ForeignKey(PoolConfiguration)
    last_cycled = models.DateTimeField(blank=True, null=True)

class Instance(models.Model):
    created = models.DateTimeField(default=timezone.now)
    pool = models.ForeignKey(InstancePool, blank=True, null=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    status_code = models.IntegerField()
    status_data = models.CharField(max_length=4095, blank=True, null=True)
    ec2_instance_id = models.CharField(max_length=255, blank=True, null=True)
    ec2_region = models.CharField(max_length=255)
    
class InstanceStatusEntry(models.Model):
    instance = models.ForeignKey(Instance)
    created = models.DateTimeField(default=timezone.now)
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)
    
class PoolStatusEntry(models.Model):
    pool = models.ForeignKey(InstancePool)
    created = models.DateTimeField(default=timezone.now)
    msg = models.CharField(max_length=4095)
    isCritical = models.BooleanField(default=False)

