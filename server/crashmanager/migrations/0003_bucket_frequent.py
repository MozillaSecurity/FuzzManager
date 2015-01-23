# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0002_bugzillatemplate_security'),
    ]

    operations = [
        migrations.AddField(
            model_name='bucket',
            name='frequent',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
