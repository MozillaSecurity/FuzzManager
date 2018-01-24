# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.files.storage  # noqa


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0017_user_restricted'),
    ]

    operations = [
        migrations.CreateModel(
            name='BucketWatch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lastCrash', models.IntegerField(default=0)),
                ('bucket', models.ForeignKey(to='crashmanager.Bucket')),
                ('user', models.ForeignKey(to='crashmanager.User')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='user',
            name='bucketsWatching',
            field=models.ManyToManyField(to='crashmanager.Bucket', through='crashmanager.BucketWatch'),
            preserve_default=True,
        ),
    ]
