# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys

from django.db import models, migrations  # noqa
from django.conf import settings  # noqa


def create_migration_tool(apps, schema_editor):
    CrashEntry = apps.get_model("crashmanager", "CrashEntry")

    for entry in CrashEntry.objects.filter(crashAddressNumeric=None):
        try:
            entry.save()
        except ValueError:
            print("Failed to convert crash address value: %s" % entry.crashAddress, file=sys.stderr)


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0008_crashentry_crashaddressnumeric'),
    ]

    operations = [
        migrations.RunPython(
            create_migration_tool,
        ),
    ]
