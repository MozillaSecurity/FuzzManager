# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0016_auto_20160308_1500'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='restricted',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
