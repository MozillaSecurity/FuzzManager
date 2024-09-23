# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from reportmanager.models import Bucket, ReportEntry


class Command(BaseCommand):
    help = "Triage a report entry into an existing bucket."

    def add_arguments(self, parser):
        parser.add_argument(
            "id",
            type=int,
            help="Report ID",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        entry = ReportEntry.objects.select_for_update().get(pk=options["id"])
        report_info = entry.get_report()

        buckets = Bucket.objects.filter(
            Q(domain=report_info.url.hostname) | Q(domain__isnull=True)
        ).order_by("-priority")

        for bucket in buckets:
            signature = bucket.get_signature()

            if signature.matches(report_info):
                entry.bucket = bucket
                break
        else:
            entry.bucket = Bucket.objects.create(
                description=f"domain is {report_info.url.hostname}",
                signature=report_info.create_signature().raw_signature,
            )

        entry.save()
