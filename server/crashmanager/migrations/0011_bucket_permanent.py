# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0010_bugzillatemplate_security_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='bucket',
            name='permanent',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
