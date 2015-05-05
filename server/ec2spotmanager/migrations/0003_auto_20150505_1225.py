# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ec2spotmanager', '0002_instancestatusentry_poolstatusentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='instancestatusentry',
            name='isCritical',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='poolstatusentry',
            name='isCritical',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
