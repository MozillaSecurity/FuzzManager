# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0015_crashentry_triagedonce'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crashentry',
            name='triagedOnce',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
