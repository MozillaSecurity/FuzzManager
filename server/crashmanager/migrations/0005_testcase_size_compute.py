# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from crashmanager.models import TestCase

def calculateSizes(apps, schema_editor):
    for testcase in TestCase.objects.all():
        testcase.loadTest()
        testcase.storeTestAndSave()

class Migration(migrations.Migration):
    dependencies = [ 
        ('crashmanager', '0004_testcase_size')
    ]

    operations = [
        migrations.RunPython(calculateSizes),
    ]
