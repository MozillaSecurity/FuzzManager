# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0007_bugzillatemplate_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='crashentry',
            name='crashAddressNumeric',
            field=models.BigIntegerField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
