# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0013_init_cachedcrashinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='bugzillatemplate',
            name='testcase_filename',
            field=models.TextField(default='', blank=True),
            preserve_default=False,
        ),
    ]
