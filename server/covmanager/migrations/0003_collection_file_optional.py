# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-20 14:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('covmanager', '0002_increase_collection_filename_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='coverage',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='covmanager.CollectionFile'),
        ),
    ]
