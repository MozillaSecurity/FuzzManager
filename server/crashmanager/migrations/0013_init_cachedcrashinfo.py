# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.db import migrations


def create_migration_tool(apps, schema_editor):
    CrashEntry = apps.get_model("crashmanager", "CrashEntry")
    for entry in CrashEntry.objects.filter(cachedCrashInfo=None):
        entry.save(update_fields=['cachedCrashInfo'])


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0012_crashentry_cachedcrashinfo'),
    ]

    operations = [
        migrations.RunPython(
            create_migration_tool,
        ),
    ]
