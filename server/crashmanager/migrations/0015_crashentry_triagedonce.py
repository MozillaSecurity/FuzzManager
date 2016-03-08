# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0014_bugzillatemplate_testcase_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='crashentry',
            name='triagedOnce',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
