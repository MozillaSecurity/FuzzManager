# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bucket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('signature', models.TextField()),
                ('shortDescription', models.CharField(max_length=1023, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Bug',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('externalId', models.CharField(max_length=255, blank=True)),
                ('closed', models.DateTimeField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BugProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('classname', models.CharField(max_length=255)),
                ('hostname', models.CharField(max_length=255)),
                ('urlTemplate', models.CharField(max_length=1023)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BugzillaTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('product', models.TextField()),
                ('component', models.TextField()),
                ('summary', models.TextField(blank=True)),
                ('version', models.TextField()),
                ('description', models.TextField(blank=True)),
                ('whiteboard', models.TextField(blank=True)),
                ('keywords', models.TextField(blank=True)),
                ('op_sys', models.TextField(blank=True)),
                ('platform', models.TextField(blank=True)),
                ('priority', models.TextField(blank=True)),
                ('severity', models.TextField(blank=True)),
                ('alias', models.TextField(blank=True)),
                ('cc', models.TextField(blank=True)),
                ('assigned_to', models.TextField(blank=True)),
                ('qa_contact', models.TextField(blank=True)),
                ('target_milestone', models.TextField(blank=True)),
                ('attrs', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CrashEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('rawStdout', models.TextField(blank=True)),
                ('rawStderr', models.TextField(blank=True)),
                ('rawCrashData', models.TextField(blank=True)),
                ('metadata', models.TextField(blank=True)),
                ('env', models.TextField(blank=True)),
                ('args', models.TextField(blank=True)),
                ('crashAddress', models.CharField(max_length=255, blank=True)),
                ('shortSignature', models.CharField(max_length=255, blank=True)),
                ('bucket', models.ForeignKey(blank=True, to='crashmanager.Bucket', null=True)),
                ('client', models.ForeignKey(to='crashmanager.Client')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OS',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=63)),
                ('version', models.CharField(max_length=127, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Platform',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=63)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=63)),
                ('version', models.CharField(max_length=127, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestCase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('test', models.FileField(storage=django.core.files.storage.FileSystemStorage(
                    location=b'/home/decoder/Mozilla/repos/FuzzManager/server'), upload_to=b'tests')),
                ('size', models.IntegerField(default=0)),
                ('quality', models.IntegerField(default=0)),
                ('isBinary', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='crashentry',
            name='os',
            field=models.ForeignKey(to='crashmanager.OS'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='crashentry',
            name='platform',
            field=models.ForeignKey(to='crashmanager.Platform'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='crashentry',
            name='product',
            field=models.ForeignKey(to='crashmanager.Product'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='crashentry',
            name='testcase',
            field=models.ForeignKey(blank=True, to='crashmanager.TestCase', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bug',
            name='externalType',
            field=models.ForeignKey(to='crashmanager.BugProvider'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bucket',
            name='bug',
            field=models.ForeignKey(blank=True, to='crashmanager.Bug', null=True),
            preserve_default=True,
        ),
    ]
