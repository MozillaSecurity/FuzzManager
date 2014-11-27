# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

class Migration(migrations.Migration):
    dependencies = [ 
        ('crashmanager', '0005_testcase_size_compute')
    ]

    operations = [
        migrations.AddField(
            model_name='Bug',
            name='closed',
            field=models.DateTimeField(default=None, blank=True, null=True),
            preserve_default=True,
        )
    ]
