# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.db import migrations
from crashmanager.models import CrashEntry

def create_migration_tool(apps, schema_editor):
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
