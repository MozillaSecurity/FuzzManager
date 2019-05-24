from django.core.exceptions import MultipleObjectsReturned  # noqa
from django.core.files.base import ContentFile
import hashlib
from rest_framework import serializers
from rest_framework.exceptions import APIException

from crashmanager.models import Client, Tool
from .models import Collection, CollectionFile, Repository, ReportConfiguration, Report


class InvalidArgumentException(APIException):
    status_code = 400


class CollectionSerializer(serializers.ModelSerializer):
    # We need to redefine several fields explicitly because we flatten our
    # foreign keys into these fields instead of using primary keys, hyperlinks
    # or slug fields. All of the other solutions would require the client to
    # create these instances first and issue multiple requests in total.
    #
    # write_only here means don't try to read it automatically in super().to_representation()
    repository = serializers.CharField(source='repository.name', max_length=255)
    client = serializers.CharField(source='client.name', max_length=255)
    tools = serializers.CharField(max_length=1023, write_only=True)
    coverage = serializers.CharField(source='coverage.file', required=False)

    class Meta:
        model = Collection
        fields = (
            'repository', 'revision', 'branch', 'tools',
            'client', 'coverage', 'description', 'id', 'created'
        )
        read_only_fields = ('id', 'created')

    def to_representation(self, obj):
        '''
        Serialize (flatten) our object. We need custom flattening because we
        want the foreign relationships of our object to be flattened into our
        object by name.
        '''
        serialized = super(CollectionSerializer, self).to_representation(obj)
        if obj is not None:
            serialized["tools"] = ",".join([x.name for x in obj.tools.all()])

        return serialized

    def create(self, attrs):
        '''
        Create a Collection instance based on the given dictionary of values
        received. We need to unflatten foreign relationships like repository,
        tool and client and create the foreign objects on the fly if they
        don't exist in our database yet.
        '''
        missing_keys = {'revision', 'coverage'} - set(attrs.keys())
        if missing_keys:
            raise InvalidArgumentException({key: ["This field is required."] for key in missing_keys})

        repository = attrs.pop('repository')['name']

        # It should not be possible to end up with an invalid repository
        # through the REST API, but we check it, just to be sure.
        repository = Repository.objects.filter(name=repository)
        if not repository:
            raise InvalidArgumentException("Invalid repository specified")

        # Also check that there is not more than one repository with the
        # specified name. If there is, then this is a configuration issue,
        # but instead of silently using the wrong repository, let's error out.
        if len(repository) > 1:
            raise InvalidArgumentException("Ambiguous repository specified")

        attrs['repository'] = repository[0]

        # Get or instantiate objects for client and tool
        attrs['client'] = Client.objects.get_or_create(name=attrs['client']['name'])[0]
        attrs['tools'] = [Tool.objects.get_or_create(name=tool)[0] for tool in attrs['tools'].split(',')]

        coverage = attrs.pop('coverage')['file']

        h = hashlib.new('sha1')
        h.update(repr(coverage).encode('utf-8'))

        dbobj = CollectionFile()
        dbobj.file.save("%s.coverage" % h.hexdigest(), ContentFile(coverage))
        dbobj.save()
        attrs['coverage'] = dbobj

        # Create our Collection instance
        return super(CollectionSerializer, self).create(attrs)


class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ('name',)
        read_only_fields = ('name',)


class ReportConfigurationSerializer(serializers.ModelSerializer):
    repository = serializers.CharField(source='repository.name', max_length=255)

    class Meta:
        model = ReportConfiguration
        fields = (
            'repository', 'description', 'directives', 'public', 'id', 'logical_parent'
        )
        read_only_fields = ('id', 'created')

    def __init__(self, *args, **kwargs):
        super(ReportConfigurationSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and hasattr(request, "GET"):
            exclude_fields = request.GET.get("__exclude", None)
            if exclude_fields:
                exclude_fields = exclude_fields.split(',')

        if exclude_fields:
            for field in exclude_fields:
                self.fields.pop(field)

    def handle_repository(self, attrs):
        '''
        When creating or updating a ReportConfiguration instance, we need to unflatten
        the foreign relationship to the repository and validate that it exists.
        '''
        repository = attrs.pop('repository')['name']

        # Check the the specified repository exists
        repository = Repository.objects.filter(name=repository)
        if not repository:
            raise InvalidArgumentException("Invalid repository specified")

        # Also check that there is not more than one repository with the
        # specified name. If there is, then this is a configuration issue,
        # but instead of silently using the wrong repository, let's error out.
        if len(repository) > 1:
            raise InvalidArgumentException("Ambiguous repository specified")

        attrs['repository'] = repository[0]

    def update(self, instance, attrs):
        self.handle_repository(attrs)

        # Update our ReportConfiguration instance
        return super(ReportConfigurationSerializer, self).update(instance, attrs)

    def create(self, attrs):
        self.handle_repository(attrs)

        # Create our ReportConfiguration instance
        return super(ReportConfigurationSerializer, self).create(attrs)


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            'id', 'data_created', 'public', 'coverage', 'is_monthly', 'is_quarterly'
        )
        read_only_fields = ('id', 'data_created', 'coverage')

    def __init__(self, *args, **kwargs):
        super(ReportSerializer, self).__init__(*args, **kwargs)

        request = self.context.get("request")
        if request and hasattr(request, "GET"):
            exclude_fields = request.GET.get("__exclude", None)
            if exclude_fields:
                exclude_fields = exclude_fields.split(',')

        if exclude_fields:
            for field in exclude_fields:
                self.fields.pop(field)
