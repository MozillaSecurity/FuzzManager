# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys

from django.db import models, migrations
from django.conf import settings

def create_migration_tool(apps, schema_editor):
    CrashEntry = apps.get_model("crashmanager", "CrashEntry")
    
    for entry in CrashEntry.objects.filter(crashAddressNumeric = None):
        if entry.crashAddress == None or len(entry.crashAddress) == 0:
            entry.crashAddressNumeric = None
            entry.save()
        else:
            try:
                entry.crashAddressNumeric = long(entry.crashAddress, 16)
                
                # Crash addresses are typically unsigned, but our database
                # can only store signed 64 bit integers. Convert to signed
                # if the value exceeds maximum value for signed 64 bit.
                if (entry.crashAddressNumeric > (2**63-1)):
                    entry.crashAddressNumeric -= 2**64
                    
                entry.save()
            except ValueError as e:
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
