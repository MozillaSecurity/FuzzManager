# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.core.files.storage
import ec2spotmanager.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Instance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('hostname', models.CharField(max_length=255, null=True, blank=True)),
                ('status_code', models.IntegerField()),
                ('status_data', models.CharField(max_length=4095, null=True, blank=True)),
                ('ec2_instance_id', models.CharField(max_length=255, null=True, blank=True)),
                ('ec2_region', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InstancePool',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_cycled', models.DateTimeField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PoolConfiguration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('size', models.IntegerField(default=1, null=True, blank=True)),
                ('cycle_interval', models.IntegerField(default=86400, null=True, blank=True)),
                ('aws_access_key_id', models.CharField(max_length=255, null=True, blank=True)),
                ('aws_secret_access_key', models.CharField(max_length=255, null=True, blank=True)),
                ('ec2_key_name', models.CharField(max_length=255, null=True, blank=True)),
                ('ec2_security_groups', models.CharField(max_length=255, null=True, blank=True)),
                ('ec2_instance_type', models.CharField(max_length=255, null=True, blank=True)),
                ('ec2_image_name', models.CharField(max_length=255, null=True, blank=True)),
                ('ec2_userdata_file', models.FileField(
                    storage=django.core.files.storage.FileSystemStorage(
                        location=b'/home/decoder/Mozilla/repos/FuzzManager/server'),
                    null=True, upload_to=ec2spotmanager.models.get_storage_path, blank=True)),
                ('ec2_userdata_macros', models.CharField(max_length=4095, null=True, blank=True)),
                ('ec2_allowed_regions', models.CharField(max_length=1023, null=True, blank=True)),
                ('ec2_max_price', models.DecimalField(null=True, max_digits=12, decimal_places=6, blank=True)),
                ('ec2_tags', models.CharField(max_length=1023, null=True, blank=True)),
                ('ec2_raw_config', models.CharField(max_length=4095, null=True, blank=True)),
                ('parent', models.ForeignKey(blank=True, to='ec2spotmanager.PoolConfiguration', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='instancepool',
            name='config',
            field=models.ForeignKey(to='ec2spotmanager.PoolConfiguration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instance',
            name='pool',
            field=models.ForeignKey(blank=True, to='ec2spotmanager.InstancePool', null=True),
            preserve_default=True,
        ),
    ]
