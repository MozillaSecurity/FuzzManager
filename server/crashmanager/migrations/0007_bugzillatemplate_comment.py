# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0006_user_defaultproviderid'),
    ]

    operations = [
        migrations.AddField(
            model_name='bugzillatemplate',
            name='comment',
            field=models.TextField(default='', blank=True),
            preserve_default=False,
        ),
    ]
