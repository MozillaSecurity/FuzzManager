# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from celeryconf import app
from django.core.management import call_command

from . import cron  # noqa ensure cron tasks get registered


@app.task(ignore_result=True)
def triage_new_report(pk):
    call_command("triage_new_report", pk)
