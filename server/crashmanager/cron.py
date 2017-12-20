import os
import shutil
from tempfile import mkstemp

from django.core.management import call_command

from celeryconf import app

SIGNATURES_ZIP = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, 'files', 'signatures.zip'))


@app.task
def bug_update_status():
    call_command('bug_update_status')


@app.task
def cleanup_old_crashes():
    call_command('cleanup_old_crashes')


@app.task
def triage_new_crashes():
    call_command('triage_new_crashes')


@app.task
def export_signatures():
    fd, tmpf = mkstemp(prefix="fm-sigs-", suffix=".zip")
    os.close(fd)
    try:
        call_command('export_signatures', tmpf)
        os.chmod(tmpf, 0o644)
        shutil.copy(tmpf, SIGNATURES_ZIP)
    finally:
        os.unlink(tmpf)
