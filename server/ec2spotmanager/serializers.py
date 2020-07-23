import itertools
from django.http.response import Http404  # noqa
from rest_framework import serializers

from ec2spotmanager.models import Instance


class PoolConfigurationSerializer(serializers.BaseSerializer):
    id = serializers.IntegerField(read_only=True)
    parent = serializers.IntegerField(min_value=0, allow_null=True)
    name = serializers.CharField(max_length=255)
    size = serializers.IntegerField(min_value=1, allow_null=True)
    cycle_interval = serializers.IntegerField(min_value=0, allow_null=True)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=6, allow_null=True)
    instance_tags = serializers.DictField(child=serializers.CharField(), allow_null=True)
    instance_tags_override = serializers.BooleanField(default=False)
    ec2_key_name = serializers.CharField(max_length=255, allow_blank=True, allow_null=True)
    ec2_image_name = serializers.CharField(max_length=255, allow_blank=True, allow_null=True)
    ec2_allowed_regions = serializers.ListField(child=serializers.CharField(), allow_null=True)
    ec2_allowed_regions_override = serializers.BooleanField(default=False)
    ec2_instance_types = serializers.ListField(child=serializers.CharField(), allow_null=True)
    ec2_instance_types_override = serializers.BooleanField(default=False)
    ec2_raw_config = serializers.DictField(child=serializers.CharField(), allow_null=True)
    ec2_raw_config_override = serializers.BooleanField(default=False)
    ec2_security_groups = serializers.ListField(child=serializers.CharField(), allow_null=True)
    ec2_security_groups_override = serializers.BooleanField(default=False)
    ec2_userdata_macros = serializers.DictField(child=serializers.CharField(), allow_null=True)
    ec2_userdata_macros_override = serializers.BooleanField(default=False)
    gce_machine_types = serializers.ListField(child=serializers.CharField(), allow_null=True)
    gce_machine_types_override = serializers.BooleanField(default=False)
    gce_image_name = serializers.CharField(max_length=255, allow_blank=True, allow_null=True)
    gce_container_name = serializers.CharField(max_length=512, allow_blank=True, allow_null=True)
    gce_docker_privileged = serializers.BooleanField(default=False)
    gce_disk_size = serializers.IntegerField(min_value=1, allow_null=True)
    gce_cmd = serializers.DictField(child=serializers.CharField(), allow_null=True)
    gce_cmd_override = serializers.BooleanField(default=False)
    gce_args = serializers.DictField(child=serializers.CharField(), allow_null=True)
    gce_args_override = serializers.BooleanField(default=False)
    gce_env = serializers.DictField(child=serializers.CharField(), allow_null=True)
    gce_env_override = serializers.BooleanField(default=False)
    gce_env_include_macros = serializers.BooleanField(default=False)
    gce_raw_config = serializers.DictField(child=serializers.CharField(), allow_null=True)
    gce_raw_config_override = serializers.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        self._flatten = kwargs.pop('flatten', False)
        super(PoolConfigurationSerializer, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        result = {
            'name': obj.name,
            'id': obj.id,
            'parent': obj.parent,
        }
        if obj.parent is not None:
            result['parent'] = obj.parent.pk
        if self._flatten:
            flattened = obj.flatten()
            for field in itertools.chain(obj.config_fields, obj.list_config_fields, obj.dict_config_fields):
                if field == 'ec2_userdata':
                    continue
                result[field] = flattened.get(field, None)
        else:
            obj.deserializeFields()
            for field in obj.config_fields:
                if field == 'ec2_userdata':
                    continue
                result[field] = getattr(obj, field)
            for field in obj.list_config_fields:
                result[field] = getattr(obj, field + '_list')
            for field in obj.dict_config_fields:
                result[field] = getattr(obj, field + '_dict')
        for field in itertools.chain(obj.list_config_fields, obj.dict_config_fields):
            result[field + '_override'] = getattr(obj, field + '_override')
        return result


class MachineStatusSerializer(serializers.ModelSerializer):
    status_data = serializers.CharField(max_length=4095)

    class Meta:
        model = Instance
        fields = ['status_data']

    def update(self, instance, attrs):
        '''
        Update the status_data field of a given instance
        '''
        # Update status_data only, ignore any other data
        status_data = attrs.get('status_data', None)
        instance.status_data = status_data

        instance.save()
        return instance
