# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('crashmanager', '0018_auto_20170620_1503')
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('description', models.CharField(max_length=1023, blank=True)),
                ('revision', models.CharField(max_length=255)),
                ('branch', models.CharField(max_length=255, blank=True)),
                ('client', models.ForeignKey(to='crashmanager.Client', on_delete=models.deletion.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CollectionFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.FileField(storage=django.core.files.storage.FileSystemStorage(location=None),
                                          upload_to=b'coverage')),
                ('format', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('classname', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('location', models.CharField(max_length=1023)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='collection',
            name='coverage',
            field=models.ForeignKey(to='covmanager.CollectionFile', on_delete=models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='collection',
            name='repository',
            field=models.ForeignKey(to='covmanager.Repository', on_delete=models.deletion.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='collection',
            name='tools',
            field=models.ManyToManyField(to='crashmanager.Tool'),
            preserve_default=True,
        ),
    ]
