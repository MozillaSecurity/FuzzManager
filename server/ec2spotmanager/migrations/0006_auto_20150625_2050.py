# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import ec2spotmanager.models  # noqa


class Migration(migrations.Migration):

    dependencies = [
        ('ec2spotmanager', '0005_auto_20150520_1517'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='ec2_zone',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]
