# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ec2spotmanager', '0003_auto_20150505_1225'),
    ]

    operations = [
        migrations.AddField(
            model_name='instancepool',
            name='isEnabled',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='poolstatusentry',
            name='type',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
