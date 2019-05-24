import logging
import requests

from celeryconf import app
from dateutil.relativedelta import relativedelta, MO
from django.conf import settings
from django.db.models import Q

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


def create_weekly_report_mc(revision):
    from crashmanager.models import Client
    from .models import Collection, Repository, Report
    from .tasks import aggregate_coverage_data

    # Some of our builds (e.g. JS shell) use the HG short revision format
    # to submit their coverage while the server provides the full revision.
    short_revision = revision[:12]

    repository = Repository.objects.get(name="mozilla-central")
    client = Client.objects.get_or_create(name="Server")[0]

    collections = Collection.objects.filter(
        Q(revision=revision) | Q(revision=short_revision)).filter(
            repository=repository, coverage__isnull=False)

    last_monday = collections.first().created + relativedelta(weekday=MO(-1))

    mergedCollection = Collection()
    mergedCollection.description = "Weekly Report (Week of %s, %s reports)" % (
        last_monday.strftime("%-m/%-d"), collections.count())
    mergedCollection.repository = repository
    mergedCollection.revision = revision
    mergedCollection.branch = "master"
    mergedCollection.client = client
    mergedCollection.coverage = None
    mergedCollection.save()

    report = Report()
    report.coverage = mergedCollection
    report.data_created = last_monday
    report.save()

    # New set of tools is the combination of all tools involved
    tools = []
    for collection in collections:
        tools.extend(collection.tools.all())
    mergedCollection.tools.add(*tools)

    ids = list(collections.values_list('id', flat=True))

    aggregate_coverage_data.delay(mergedCollection.pk, ids)


@app.task(ignore_result=True)
def create_current_weekly_report_mc():
    COVERAGE_REVISION_URL = getattr(settings, 'COVERAGE_REVISION_URL', None)

    if not COVERAGE_REVISION_URL:
        logger.error("Missing configuration for COVERAGE_REVISION_URL.")
        return

    response = requests.get(COVERAGE_REVISION_URL)
    if not response.ok:
        logger.error("Failed fetching coverage revision. Got status %s with response: %s",
                     response.status_code, response.text)
        return

    revision = response.text.rstrip()
    create_weekly_report_mc(revision)
