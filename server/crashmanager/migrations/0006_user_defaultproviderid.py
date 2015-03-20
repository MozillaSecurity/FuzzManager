# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0005_add_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='defaultProviderId',
            field=models.IntegerField(default=1),
            preserve_default=True,
        ),
    ]
