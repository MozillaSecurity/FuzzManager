from django.core.exceptions import MultipleObjectsReturned
from django.core.files.base import ContentFile
from django.forms import widgets
import hashlib
from rest_framework import serializers
from rest_framework.exceptions import APIException

from crashmanager.models import Client, Tool
from .models import Collection, CollectionFile, Repository

class InvalidArgumentException(APIException):
    status_code = 400

class CollectionSerializer(serializers.ModelSerializer):
    # We need to redefine several fields explicitly because we flatten our
    # foreign keys into these fields instead of using primary keys, hyperlinks
    # or slug fields. All of the other solutions would require the client to
    # create these instances first and issue multiple requests in total.
    #
    # write_only here means don't try to read it automatically in super().to_native()
    repository = serializers.CharField(max_length=255, write_only=True)
    client = serializers.CharField(max_length=255, write_only=True)
    tools = serializers.CharField(max_length=1023, write_only=True)
    coverage = serializers.CharField(widget=widgets.Textarea, required=False)

    class Meta:
        model = Collection
        fields = (
                  'repository', 'revision', 'branch', 'tools',
                  'client', 'coverage', 'description', 'id'
                  )
        read_only_fields = ('id',)

    def to_native(self, obj):
        '''
        Serialize (flatten) our object. We need custom flattening because we
        want the foreign relationships of our object to be flattened into our
        object by name.
        '''
        serialized = super(CollectionSerializer, self).to_native(obj)
        if obj != None:
            serialized["repository"] = obj.repository.name
            serialized["client"] = obj.client.name
            serialized["tools"] = ",".join([x.name for x in obj.tools.all()])
            serialized["coverage"] = str(obj.coverage.file)

        return serialized

    def restore_object(self, attrs, instance=None):
        '''
        Create a Collection instance based on the given dictionary of values
        received. We need to unflatten foreign relationships like repository,
        tool and client and create the foreign objects on the fly if they
        don't exist in our database yet.
        '''
        if instance:
            # Not allowed to update existing instances
            return instance

        missing_keys = {'revision', 'coverage'} - set(attrs.keys())
        if missing_keys:
            raise InvalidArgumentException({key: ["This field is required."] for key in missing_keys})

        repository = attrs.pop('repository', None)

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

        client = attrs.pop('client', None)
        tools = attrs.pop('tools', None)
        coverage = attrs.pop('coverage', None)


        def createOrGetModelByName(model, attrs):
            '''
            Generically determine if the given model with the given attributes
            already exists in our database. If so, return that object, otherwise
            create it on the fly.
            
            @type model: Class
            @param model: The model to use for filtering and instantiating
            
            @type attrs: dict
            @param attrs: Dictionary of attributes to use for filtering/instantiating
            
            @rtype: model
            @return The model instance
            '''
            objs = model.objects.filter(**attrs)

            if len(objs) > 1:
                raise MultipleObjectsReturned("Multiple objects with same keyword combination in database!")

            if len(objs) == 0:
                dbobj = model(**attrs)
                dbobj.save()
                return dbobj
            else:
                return objs.first()

        # Get or instantiate objects for client and tool
        attrs['client'] = createOrGetModelByName(Client, { 'name' : client })

        tools = tools.split(",")
        toolsobjs = []
        for tool in tools:
            toolsobjs.append(createOrGetModelByName(Tool, { 'name' : tool }))

        attrs['tools'] = toolsobjs

        h = hashlib.new('sha1')
        h.update(repr(coverage))

        dbobj = CollectionFile()
        dbobj.file.save("%s.coverage" % h.hexdigest(), ContentFile(coverage))
        dbobj.save()
        attrs['coverage'] = dbobj

        # Create our Collection instance
        return super(CollectionSerializer, self).restore_object(attrs, instance)

class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = ('name',)
        read_only_fields = ('name',)
