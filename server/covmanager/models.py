from django.conf import settings
from django.contrib.auth.models import User as DjangoUser  # noqa
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.utils import timezone
import codecs
import json

from crashmanager.models import Client, Tool
from FTB import CoverageHelper

if getattr(settings, 'USE_CELERY', None):
    from .tasks import check_revision_update


class Repository(models.Model):
    classname = models.CharField(max_length=255, blank=False)
    name = models.CharField(max_length=255, blank=False)
    location = models.CharField(max_length=1023, blank=False)

    def getInstance(self):
        # Dynamically instantiate the provider as requested
        providerModule = __import__('covmanager.SourceCodeProvider.%s' % self.classname, fromlist=[self.classname])
        providerClass = getattr(providerModule, self.classname)
        return providerClass(self.location)


class CollectionFile(models.Model):
    file = models.FileField(storage=FileSystemStorage(location=getattr(settings, 'COV_STORAGE', None)),
                            max_length=255,
                            upload_to="coverage")
    format = models.IntegerField(default=0)


class Collection(models.Model):
    created = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=1023, blank=True)
    repository = models.ForeignKey(Repository, on_delete=models.deletion.CASCADE)
    revision = models.CharField(max_length=255, blank=False)
    branch = models.CharField(max_length=255, blank=True)
    tools = models.ManyToManyField(Tool)
    client = models.ForeignKey(Client, on_delete=models.deletion.CASCADE)
    coverage = models.ForeignKey(CollectionFile, blank=True, null=True, on_delete=models.deletion.CASCADE)

    def __init__(self, *args, **kwargs):
        # This variable can hold the deserialized contents of the coverage blob
        self.content = None

        # A list of fields that can be checked by a simple search query
        self.simple_query_fields = [
            "created",
            "description",
            "repository__name",
            "revision",
            "branch",
            "client__name",
            "tools__name"
        ]

        # For performance reasons we do not deserialize this field
        # automatically here. You need to explicitly call the
        # loadCoverage method if you need this data.

        super(Collection, self).__init__(*args, **kwargs)

    def loadCoverage(self):
        self.coverage.file.open(mode='rb')
        self.content = json.load(codecs.getreader('utf-8')(self.coverage.file))
        self.coverage.file.close()

    def annotateSource(self, path, coverage):
        """
        Annotate the source code to the given (leaf) coverage object by querying
        the SourceCodeProvider registered for the repository associated with this
        collection. The resulting source code is added to a "source" property in
        the object.

        @type path: string
        @param path: The path to the source code that this coverage belongs to.

        @type coverage: dict
        @param coverage: The coverage object to annotate. Should be a leaf object,
                         any children are ignored. The coverage object is directly
                         altered for performance reasons.
        """
        provider = self.repository.getInstance()
        coverage["source"] = provider.getSource(path, self.revision)

    def subset(self, path, report_configuration=None):
        """
        Calculate a subset of the coverage stored in this collection
        based on the given path.

        @type path: string
        @param path: The path to reduce to. It is expected to use forward
                     slashes. The path is interpreted as relative to the root
                     of the collection.

        @rtype: dict
        @return: An object that represents the requested subset of the coverage.
                 The storage format is the same as the underlying coverage uses.

                 None is returned if the path does not exist in the collection.
        """
        # Load coverage from disk if we haven't done that yet
        if not self.content:
            self.loadCoverage()

        if report_configuration is not None:
            report_configuration.apply(self.content)

        names = [x for x in path.split("/") if x != ""]

        if not names:
            # Querying an empty path means requesting the whole collection
            return self.content

        try:
            ret = self.content["children"]
            for name in names[:-1]:
                ret = ret[name]["children"]
            ret = ret[names[-1]]
        except KeyError:
            return None

        return ret

    @staticmethod
    def remove_childrens_children(coverage):
        """
        This method strips the children of any child nodes in the given coverage.
        Doing so saves data and processing time for other algorithms as for many
        views, the children of children are not relevant (only one depth of view
        at a time).

        @type coverage: dict
        @param coverage: A coverage data object in server-side storage format.
                         This object is directly modified by this method for
                         for performance. If you need the original object, you
                         must create a copy and pass it to this method instead.
        """
        if "children" in coverage:
            for child in coverage["children"]:
                if "children" in coverage["children"][child]:
                    # We don't remove the "children" key here because it is
                    # still required (e.g. by the UI) to determine if a child
                    # is a folder itself or not.
                    coverage["children"][child]["children"] = True

    @staticmethod
    def strip(coverage):
        """
        This method strips all detailed coverage information from the given
        coverage data. Only the summarized coverage fields are left intact.

        @type coverage: dict
        @param coverage: A coverage data object in server-side storage format.
                         This object is directly modified by this method for
                         for performance. If you need the original object, you
                         must create a copy and pass it to this method instead.
        """
        if "children" in coverage and type(coverage["children"]) != bool:
            for child in coverage["children"]:
                Collection.strip(coverage["children"][child])
        else:
            # This is a leaf, so we need to delete coverage data.
            # However, passing in an already stripped object to this
            # method shouldn't error, so we accept the error that the
            # coverage field might not be present.
            coverage.pop("coverage", None)


# This post_delete handler ensures that the corresponding coverage
# file is deleted when the Collection is gone.
@receiver(post_delete, sender=Collection)
def Collection_delete(sender, instance, **kwargs):
    if instance.coverage:
        instance.coverage.file.delete(False)
        instance.coverage.delete(False)


# post_save handler for celery integration
if getattr(settings, 'USE_CELERY', None):
    @receiver(post_save, sender=Collection)
    def Collection_save(sender, instance, **kwargs):
        check_revision_update.delay(instance.pk)


class ReportConfiguration(models.Model):
    description = models.CharField(max_length=1023, blank=True)
    repository = models.ForeignKey(Repository, on_delete=models.deletion.CASCADE)
    directives = models.TextField()
    public = models.BooleanField(blank=False, default=False)
    logical_parent = models.ForeignKey("self", blank=True, null=True, on_delete=models.deletion.CASCADE)

    def apply(self, collection):
        CoverageHelper.apply_include_exclude_directives(collection, self.directives.splitlines())
        CoverageHelper.calculate_summary_fields(collection)


class ReportSummary(models.Model):
    collection = models.OneToOneField(Collection, on_delete=models.deletion.CASCADE)
    cached_result = models.TextField(null=True, blank=True)


class Report(models.Model):
    # This field is used to store the date when the data itself was created.
    # In particular, this is *not* necessarily the same as coverage.created
    # because aggregated collections can be created later, losing the original
    # creation dates. This date will be used as a reference time frame to
    # determine week, month, quarter, etc. for displaying purposes.
    data_created = models.DateTimeField(default=timezone.now)
    public = models.BooleanField(blank=False, default=False)
    coverage = models.ForeignKey(Collection, blank=False, null=False, on_delete=models.deletion.CASCADE)

    is_monthly = models.BooleanField(blank=False, default=False)
    is_quarterly = models.BooleanField(blank=False, default=False)
