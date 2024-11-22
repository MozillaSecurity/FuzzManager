# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
from logging import getLogger
from urllib.parse import urlsplit

from dateutil.parser import isoparse
from django.conf import settings
from django.core.management import BaseCommand
from django.db.utils import IntegrityError
from django.utils import timezone
from google.cloud import bigquery
from google.oauth2 import service_account

from reportmanager.models import ReportEntry
from webcompat.models import Report

LOG = getLogger("reportmanager.import")


class Command(BaseCommand):
    help = "Import reports from BigQuery"

    def handle(self, *args, **options):
        params = {
            "project": settings.BIGQUERY_PROJECT,
        }
        if svc_acct := getattr(settings, "BIGQUERY_SERVICE_ACCOUNT", None):
            params["credentials"] = (
                service_account.Credentials.from_service_account_info(svc_acct)
            )

        client = bigquery.Client(**params)
        result = client.query_and_wait(
            f"SELECT * FROM `{settings.BIGQUERY_TABLE}` WHERE reported_at >= @since;",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("since", "DATETIME", options["since"])
                ]
            ),
        )

        for row in result:
            if row.comments is None:
                continue
            report_obj = Report(
                app_name=row.app_name,
                app_channel=row.app_channel,
                app_version=row.app_version,
                breakage_category=row.breakage_category,
                comments=row.comments,
                details=json.loads(row.details),
                reported_at=row.reported_at.replace(tzinfo=timezone.utc),
                url=urlsplit(row.url),
                os=row.os,
                uuid=row.uuid,
            )
            try:
                ReportEntry.objects.create_from_report(report_obj)
            except IntegrityError as exc:
                LOG.error("creating report entry: %s", exc)

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            help="date/time in ISO 8601 format",
            type=isoparse,
            required=True,
        )
