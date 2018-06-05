# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('covmanager', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collectionfile',
            name='file',
            field=models.FileField(max_length=255, storage=django.core.files.storage.FileSystemStorage(location=None),
                                   upload_to=b'coverage'),
        ),
    ]
