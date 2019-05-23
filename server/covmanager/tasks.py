from django.conf import settings  # noqa
from django.core.files.base import ContentFile

from celeryconf import app  # noqa
from . import cron  # noqa ensure cron tasks get registered

import copy
import hashlib
import json


@app.task(ignore_result=True)
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


@app.task(ignore_result=True)
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
    total_stats = None

    for collection in collections[1:]:
        # Load coverage, perform the merge, then release reference to the JSON blob again
        collection.loadCoverage()
        stats = CoverageHelper.merge_coverage_data(newCoverage, collection.content)
        collection.content = None

        # Merge stats appropriately
        if total_stats is None:
            total_stats = stats
        else:
            for x in total_stats:
                total_stats[x] += stats[x]

    # Save the new coverage blob to disk and database
    newCoverage = json.dumps(newCoverage, separators=(',', ':'))
    h = hashlib.new('sha1')
    h.update(newCoverage.encode('utf-8'))
    dbobj = CollectionFile()
    dbobj.file.save("%s.coverage" % h.hexdigest(), ContentFile(newCoverage))
    dbobj.save()

    mergedCollection.description += " (NC %s, LM %s, CM %s)" % (stats['null_coverable_count'],
                                                                stats['length_mismatch_count'],
                                                                stats['coverable_mismatch_count'])

    # Save the collection
    mergedCollection.coverage = dbobj
    mergedCollection.save()

    return


@app.task(ignore_result=True)
def calculate_report_summary(pk):
    from covmanager.models import ReportConfiguration, ReportSummary
    summary = ReportSummary.objects.get(pk=pk)

    # Load coverage data
    collection = summary.collection
    collection.loadCoverage()

    rcs = ReportConfiguration.objects.filter(public=True, repository=collection.repository)

    data = None
    waiting = {}
    arrived = {}

    for rc in rcs:
        coverage = copy.deepcopy(collection.content)
        rc.apply(coverage)
        if "children" in coverage:
            del coverage["children"]

        coverage["name"] = rc.description
        coverage["id"] = rc.pk

        if rc.logical_parent:
            # We have a parent, check if we already processed it
            if rc.logical_parent.pk in arrived:
                # Short path, parent is already there, we can link directly
                if "children" not in arrived[rc.logical_parent.pk]:
                    arrived[rc.logical_parent.pk]["children"] = []
                arrived[rc.logical_parent.pk]["children"].append(coverage)
            else:
                # Parent hasn't been processed yet, so we have to wait for it
                if rc.logical_parent.pk not in waiting:
                    waiting[rc.logical_parent.pk] = []
                waiting[rc.logical_parent.pk].append(coverage)
        elif not data:
            # This is the root
            data = coverage
        else:
            summary.cached_result = json.dumps({"error": "There are multiple root reports configured."})
            summary.save()
            return

        # Now check if anyone was waiting for us
        if rc.pk in waiting:
            coverage["children"] = waiting[rc.pk]
            del waiting[rc.pk]

        # We have arrived
        arrived[rc.pk] = coverage

    if waiting:
        # We shouldn't have orphaned reports
        data["warning"] = "There are orphaned reports that won't be displayed."

    summary.cached_result = json.dumps(data)
    summary.save()
    return
