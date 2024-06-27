import json
import logging

import requests
from celeryconf import app
from dateutil.relativedelta import MO, relativedelta
from django.conf import settings
from django.contrib.auth.models import User as DjangoUser
from django.db.models import Q
from django.urls import reverse
from notifications.signals import notify

logger = logging.getLogger("covmanager")


# The `create_current_weekly_report_mc` task and dependencies are part of the
# internal process at Mozilla to create an aggregated fuzzing coverage report
# on a weekly basis. For this purpose, a revision is fixed every week and all
# fuzzing tools perform a coverage run on the that revision (during the week).
# At the end of the week, the code below fetches all reports belonging to that
# revision (which is published as an URL) and aggregates them into a combined
# weekly report. You can use the same logic if you have a large project with
# multiple testing tools and would like to automate the process of generating
# a summarized report for your testing efforts.


def create_weekly_report_mc(revision, ipc_only=False):
    from crashmanager.models import Client

    from .models import Collection, Report, Repository
    from .tasks import aggregate_coverage_data

    # Some of our builds (e.g. JS shell) use the HG short revision format
    # to submit their coverage while the server provides the full revision.
    short_revision = revision[:12]

    repository = Repository.objects.get(name="mozilla-central")
    client = Client.objects.get_or_create(name="Server")[0]

    collections = (
        Collection.objects.filter(Q(revision=revision) | Q(revision=short_revision))
        .filter(repository=repository, coverage__isnull=False)
        .exclude(description__contains="IGNORE_MERGE")
    )

    if ipc_only:
        collections = collections.filter(description__contains="IPC")
    else:
        collections = collections.exclude(description__contains="IPC")

    last_monday = collections.first().created + relativedelta(weekday=MO(-1))

    ipc_description = ""
    if ipc_only:
        ipc_description = "IPC "

    mergedCollection = Collection()
    mergedCollection.description = "Weekly {}Report (Week of {}, {} reports)".format(
        ipc_description,
        last_monday.strftime("%-m/%-d"),
        collections.count(),
    )
    mergedCollection.repository = repository
    mergedCollection.revision = revision
    mergedCollection.branch = "master"
    mergedCollection.client = client
    mergedCollection.coverage = None
    mergedCollection.save()

    report = Report()
    report.coverage = mergedCollection
    report.data_created = last_monday
    if ipc_only:
        report.tag = "IPC"
    report.save()

    # New set of tools is the combination of all tools involved
    tools = []
    for collection in collections:
        tools.extend(collection.tools.all())
    mergedCollection.tools.add(*tools)

    ids = list(collections.values_list("id", flat=True))

    aggregate_coverage_data.apply(args=(mergedCollection.pk, ids))

    # Generate notifications for coverage drops
    identify_coverage_drops(revision, ipc_only)


def fetch_coverage_revision():
    COVERAGE_REVISION_URL = getattr(settings, "COVERAGE_REVISION_URL", None)

    if not COVERAGE_REVISION_URL:
        logger.error("Missing configuration for COVERAGE_REVISION_URL.")
        return

    response = requests.get(COVERAGE_REVISION_URL)
    if not response.ok:
        logger.error(
            "Failed fetching coverage revision. Got status %s with response: %s",
            response.status_code,
            response.text,
        )
        return

    return response.text.rstrip()


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


def identify_coverage_drops(revision, ipc_only=False):
    """Identify coverage drops by comparing the two most recent coverage summaries

    @param revision: Revision of the most recent weekly report.
    @param ipc_only: Boolean indicating we should compare IPC reports.
    """
    from crashmanager.models import User

    from .models import Collection, ReportSummary
    from .tasks import calculate_report_summary

    collections = Collection.objects.filter(
        description__startswith="Weekly Report"
    ).order_by("-created")
    if ipc_only:
        collections = tuple(collections.filter(description__contains="IPC")[:2])
    else:
        collections = tuple(collections.exclude(description__contains="IPC")[:2])

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
            calculate_report_summary.apply(args=(summary.pk,))

    # Refresh current and previous to ensure the report_summary is available
    current = Collection.objects.get(pk=current.pk)
    previous = Collection.objects.get(pk=previous.pk)

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


@app.task(ignore_result=True)
def create_current_weekly_report_mc():
    revision = fetch_coverage_revision()
    create_weekly_report_mc(revision)


@app.task(ignore_result=True)
def create_current_weekly_ipc_report_mc():
    revision = fetch_coverage_revision()
    create_weekly_report_mc(revision, ipc_only=True)
