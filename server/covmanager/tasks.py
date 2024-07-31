import copy
import hashlib
import json
import logging

from celeryconf import app
from django.conf import settings
from django.contrib.auth.models import User as DjangoUser
from django.core.files.base import ContentFile
from django.urls import reverse
from notifications.signals import notify

from . import cron  # noqa ensure cron tasks get registered

logger = logging.getLogger("covmanager")


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


def compare_coverage_summaries(old_summary, new_summary):
    """Compare coverage summaries recursively and identify coverage drops.

    @param old_summary: Older coverage summary.
    @param new_summary: Newer coverage summary.
    @return: List of report configuration names with dropped coverage.
    """
    rcs = []
    if "children" in old_summary and "children" in new_summary:
        new_children_map = {child["name"]: child for child in new_summary["children"]}
        for c1 in old_summary["children"]:
            match = new_children_map.get(c1["name"])
            if match:
                rcs.extend(compare_coverage_summaries(c1, match))

    if (
        old_summary.get("coveragePercent", 0) - new_summary.get("coveragePercent", 0)
        > settings.COVERAGE_REPORT_DELTA
    ):
        rcs.append(old_summary["name"])

    return rcs


@app.task(ignore_result=True)
def check_notify_coverage_drops(current_pk, previous_pk, retries=20):
    """Generate notification if coverage has dropped between coverage summaries

    @param current_pk: ID of current coverage summary
    @param previous_pk: ID of previous coverage summary
    """
    from crashmanager.models import User

    from .models import Collection

    current = Collection.objects.get(pk=current_pk)
    previous = Collection.objects.get(pk=previous_pk)

    if (
        current.reportsummary.cached_result is None
        or previous.reportsummary.cached_result is None
    ):
        if retries:
            # try again in 60s
            logger.info("Report summary not ready, %d retries remain", retries)
            check_notify_coverage_drops.apply_async(
                (current_pk, previous_pk), {"retries": retries - 1}, countdown=60
            )
        else:
            logger.error(
                "Failed to compare report summaries, calculation never finished? "
                "(current=%d, previous=%d)",
                current_pk,
                previous_pk,
            )
        return

    # Get list of users with the coverage_drop notification enabled
    cm_uids = User.objects.filter(coverage_drop=True).values_list("user_id", flat=True)
    django_users = DjangoUser.objects.filter(id__in=cm_uids).distinct()
    recipients = django_users.filter(user_permissions__codename="view_covmanager")

    # Compare both report summaries
    old_summary = json.loads(previous.reportsummary.cached_result)
    new_summary = json.loads(current.reportsummary.cached_result)
    coverage_drops = compare_coverage_summaries(old_summary, new_summary)

    if len(coverage_drops) > 0:
        url = f"{reverse('covmanager:collections_diff')}#ids={previous.id},{current.id}"
        notify.send(
            current,
            recipient=recipients,
            verb="coverage_drop",
            level="warning",
            description=(
                f"Drop detected in coverage collection {current.id} "
                f"in the following report configurations: {', '.join(coverage_drops)}."
            ),
            diff_url=url,
        )


def identify_coverage_drops(revision, ipc_only=False):
    """Identify coverage drops by comparing the two most recent coverage summaries

    @param revision: Revision of the most recent weekly report.
    @param ipc_only: Boolean indicating we should compare IPC reports.
    """

    from .models import Collection, ReportSummary
    from .tasks import calculate_report_summary

    query = Collection.objects.all()
    if ipc_only:
        query = query.filter(description__startswith="Weekly IPC Report")
    else:
        query = query.filter(description__startswith="Weekly Report")
    query = query.order_by("-created")[:2]
    collections = tuple(query)

    if len(collections) != 2:
        logger.warning(
            "Not enough reports found. Expected at least 2, found %d.",
            len(collections),
        )
        return

    current, previous = collections
    if not current.revision == revision:
        logger.error(
            "Mismatch in report revisions. Current revision: %s, expected revision: %s",
            current.revision,
            revision,
        )
        return

    for collection in collections:
        if not hasattr(collection, "reportsummary"):
            summary = ReportSummary(collection=collection, cached_result=None)
            summary.save()
            calculate_report_summary.delay(summary.pk)

    check_notify_coverage_drops.delay(current.pk, previous.pk)


@app.task(ignore_result=True)
def aggregate_coverage_data(pk, pks):
    from covmanager.models import Collection, CollectionFile
    from FTB import CoverageHelper

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
        # Load coverage, perform the merge, then release reference to the JSON blob
        # again
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
    newCoverage = json.dumps(newCoverage, separators=(",", ":"))
    h = hashlib.new("sha1")
    h.update(newCoverage.encode("utf-8"))
    dbobj = CollectionFile()
    dbobj.file.save(f"{h.hexdigest()}.coverage", ContentFile(newCoverage))
    dbobj.save()

    if total_stats:
        mergedCollection.description += " (NC {}, LM {}, CM {})".format(
            total_stats["null_coverable_count"],
            total_stats["length_mismatch_count"],
            total_stats["coverable_mismatch_count"],
        )

    # Save the collection
    mergedCollection.coverage = dbobj
    mergedCollection.save()

    # Generate notifications for coverage drops
    if mergedCollection.description.startswith("Weekly IPC Report"):
        identify_coverage_drops(mergedCollection.revision, ipc_only=True)
    elif mergedCollection.description.startswith("Weekly Report"):
        identify_coverage_drops(mergedCollection.revision, ipc_only=False)


@app.task(ignore_result=True)
def calculate_report_summary(pk):
    from covmanager.models import ReportConfiguration, ReportSummary

    summary = ReportSummary.objects.get(pk=pk)

    # Load coverage data
    collection = summary.collection
    collection.loadCoverage()

    rcs = ReportConfiguration.objects.filter(
        public=True, repository=collection.repository
    )

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
            summary.cached_result = json.dumps(
                {"error": "There are multiple root reports configured."}
            )
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
