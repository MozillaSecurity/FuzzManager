from django.http.response import Http404
from rest_framework import serializers

from ec2spotmanager.models import Instance


class MachineStatusSerializer(serializers.ModelSerializer):
    status_data = serializers.CharField(max_length=4095)

    class Meta:
        model = Instance
        fields = ['status_data']

    def to_native(self, obj):
        '''
        Serialize (flatten) our object.
        '''
        serialized = super(MachineStatusSerializer, self).to_native(obj)
        if obj != None:
            # Do stuff with serialized object, e.g. removing fields
            pass

        return serialized

    def update(self, instance, attrs):
        '''
        Update the status_data field of a given instance
        '''
        # Update status_data only, ignore any other data
        status_data = attrs.get('status_data', None)
        instance.status_data = status_data

        instance.save()
        return instance
