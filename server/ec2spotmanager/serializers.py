from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from ec2spotmanager.models import Instance

class MachineStatusSerializer(serializers.ModelSerializer):
    client = serializers.CharField(max_length=255)
    status_data = serializers.CharField(max_length=4095)

    class Meta:
        model = Instance
        fields = ('status_data')

    def to_native(self, obj):
        '''
        Serialize (flatten) our object.
        '''
        serialized = super(MachineStatusSerializer, self).to_native(obj)
        if obj != None:
            # Do stuff with serialized object, e.g. removing fields
            pass

        return serialized

    def restore_object(self, attrs, instance=None):
        '''
        Update the status_data field of a given instance
        '''
        if not instance:
            # Try finding the instance by specified client id
            client = attrs.pop('client', None)

            if not client:
                return None

            instance = get_object_or_404(Instance, hostname=client)

        # Update status_data only, ignore any other data
        status_data = attrs.pop('status_data', None)
        instance.status_data = status_data

        # Create our CrashEntry instance
        return super(MachineStatusSerializer, self).restore_object(attrs, instance)
