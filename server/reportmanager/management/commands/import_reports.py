# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from pathlib import Path

from django.core.management import BaseCommand

from reportmanager.models import ReportEntry
from webcompat.models import Report


class Command(BaseCommand):
    help = "Import a report file (one report per line)"

    def handle(self, *args, **options):
        for report_path in options["reports"]:
            with report_path.open() as report_file:
                for report in report_file:
                    report_obj = Report.load(report)
                    ReportEntry.objects.create_from_report(report_obj)

    def add_arguments(self, parser):
        def existing_path(arg):
            result = Path(arg)
            if not result.is_file():
                raise TypeError()
            return result

        parser.add_argument(
            "reports",
            nargs="+",
            type=existing_path,
        )
