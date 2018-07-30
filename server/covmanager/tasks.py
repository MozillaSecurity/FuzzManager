from django.conf import settings  # noqa
from django.core.files.base import ContentFile

from celeryconf import app  # noqa

import hashlib
import json


@app.task
def check_revision_update(pk):
    from covmanager.models import Collection, Repository  # noqa
    collection = Collection.objects.get(pk=pk)

    # Get the SourceCodeProvider associated with this collection
    provider = collection.repository.getInstance()

    # Check if the provider knows the specified revision
    if not provider.testRevision(collection.revision):
        # If not, update the repository
        provider.update()

    # TODO: We could double-check here that the revision is now known
    # and raise an error if not. This error would have to be propagated
    # to the user and since we already saved the collection, we can't
    # reject the client anymore.

    return


@app.task
def aggregate_coverage_data(pk, pks):
    from covmanager.models import Collection, CollectionFile  # noqa
    from FTB import CoverageHelper # noqa

    # Fetch our existing, but incomplete destination collection
    mergedCollection = Collection.objects.get(pk=pk)

    # Fetch all source collections
    collections = Collection.objects.filter(pk__in=pks)

    # Merge the coverage of all other collections into the first one
    first_collection = collections[0]
    first_collection.loadCoverage()
    newCoverage = first_collection.content
    for collection in collections[1:]:
        # Load coverage, perform the merge, then release reference to the JSON blob again
        collection.loadCoverage()
        CoverageHelper.merge_coverage_data(newCoverage, collection.content)
        collection.content = None

    # Save the new coverage blob to disk and database
    newCoverage = json.dumps(newCoverage, separators=(',', ':'))
    h = hashlib.new('sha1')
    h.update(newCoverage.encode('utf-8'))
    dbobj = CollectionFile()
    dbobj.file.save("%s.coverage" % h.hexdigest(), ContentFile(newCoverage))
    dbobj.save()

    # Save the collection
    mergedCollection.coverage = dbobj
    mergedCollection.save()

    return
