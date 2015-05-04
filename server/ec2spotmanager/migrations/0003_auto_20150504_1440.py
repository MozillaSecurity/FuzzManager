# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ec2spotmanager', '0002_instancestatusentry_poolstatusentry'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='poolstatusentry',
            name='instance',
        ),
        migrations.AddField(
            model_name='poolstatusentry',
            name='pool',
            field=models.ForeignKey(default=0, to='ec2spotmanager.InstancePool'),
            preserve_default=False,
        ),
    ]
