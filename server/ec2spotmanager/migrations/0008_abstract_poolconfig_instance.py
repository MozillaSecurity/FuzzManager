# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import ec2spotmanager.models


# XXX(truber): for some reason when using multi-table inheritance, fields in the base must be removed before the
# sub-model can be created (even with different fields), removing a field from a base class doesn't work
#
# FieldError: Local field u'aws_access_key_id' in class 'EC2PoolConfiguration' clashes with field of the same name from
#             base class 'PoolConfiguration'.
#
# ... even if I give aws_access_key_id a temporary name in the sub-model until after it is removed from the base model


INSTANCE_FIELDS = ['status_code',
                   'status_data',
                   'ec2_instance_id',
                   'ec2_region',
                   'ec2_zone']
INSTANCE_DATA = {}


POOL_CONFIGURATION_FIELDS = ['aws_access_key_id',
                             'aws_secret_access_key',
                             'ec2_allowed_regions',
                             'ec2_image_name',
                             'ec2_instance_types',
                             'ec2_key_name',
                             'ec2_max_price',
                             'ec2_raw_config',
                             'ec2_security_groups',
                             'ec2_tags',
                             'ec2_userdata_file',
                             'ec2_userdata_macros']
POOL_CONFIGURATION_DATA = {}


def save_data(apps, schema_editor):
    Instance = apps.get_model('ec2spotmanager', 'Instance')
    PoolConfiguration = apps.get_model('ec2spotmanager', 'PoolConfiguration')
    db_alias = schema_editor.connection.alias

    INSTANCE_DATA.clear()
    for inst in Instance.objects.using(db_alias).all():
        INSTANCE_DATA[inst.pk] = {field: getattr(inst, field) for field in INSTANCE_FIELDS}

    POOL_CONFIGURATION_DATA.clear()
    for config in PoolConfiguration.objects.using(db_alias).all():
        POOL_CONFIGURATION_DATA[config.pk] = {field: getattr(config, field) for field in POOL_CONFIGURATION_FIELDS}
        if not POOL_CONFIGURATION_DATA[config.pk]["ec2_userdata_file"]:
            del POOL_CONFIGURATION_DATA[config.pk]["ec2_userdata_file"]
        if all(value is None for value in POOL_CONFIGURATION_DATA[config.pk].values()):
            del POOL_CONFIGURATION_DATA[config.pk]


def restore_data(apps, schema_editor):
    EC2Instance = apps.get_model('ec2spotmanager', 'EC2Instance')
    EC2PoolConfiguration = apps.get_model('ec2spotmanager', 'EC2PoolConfiguration')
    db_alias = schema_editor.connection.alias

    for pk, data in INSTANCE_DATA.items():
        inst = EC2Instance.objects.using(db_alias).create(pk=pk)
        for field, value in data.items():
            setattr(inst, field, value)
        inst.save()
    INSTANCE_DATA.clear()

    for pk, data in POOL_CONFIGURATION_DATA.items():
        config = EC2PoolConfiguration.objects.using(db_alias).create(pk=pk)
        for field, value in data.items():
            setattr(config, field, value)
        config.save()
    POOL_CONFIGURATION_DATA.clear()


def reverse_save_data(apps, schema_editor):
    EC2Instance = apps.get_model('ec2spotmanager', 'EC2Instance')
    EC2PoolConfiguration = apps.get_model('ec2spotmanager', 'EC2PoolConfiguration')
    db_alias = schema_editor.connection.alias

    INSTANCE_DATA.clear()
    for inst in EC2Instance.objects.using(db_alias).all():
        INSTANCE_DATA[inst.pk] = {field: getattr(inst, field) for field in INSTANCE_FIELDS}

    POOL_CONFIGURATION_DATA.clear()
    for config in EC2PoolConfiguration.objects.using(db_alias).all():
        POOL_CONFIGURATION_DATA[config.pk] = {field: getattr(config, field) for field in POOL_CONFIGURATION_FIELDS}


def reverse_restore_data(apps, schema_editor):
    Instance = apps.get_model('ec2spotmanager', 'Instance')
    PoolConfiguration = apps.get_model('ec2spotmanager', 'PoolConfiguration')
    db_alias = schema_editor.connection.alias

    for pk, data in INSTANCE_DATA.items():
        inst = Instance.objects.using(db_alias).get(pk=pk)
        for field, value in data.items():
            setattr(inst, field, value)
        inst.save()
    INSTANCE_DATA.clear()

    for pk, data in POOL_CONFIGURATION_DATA.items():
        config = PoolConfiguration.objects.using(db_alias).get(pk=pk)
        for field, value in data.items():
            setattr(config, field, value)
        config.save()
    POOL_CONFIGURATION_DATA.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('ec2spotmanager', '0007_instance_type_to_list'),
    ]

    operations = [
        migrations.RunPython(save_data, reverse_restore_data),
        migrations.RemoveField(
            model_name='instance',
            name='ec2_instance_id',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='ec2_region',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='ec2_zone',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='status_code',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='status_data',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='aws_access_key_id',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='aws_secret_access_key',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_allowed_regions',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_image_name',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_instance_types',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_key_name',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_max_price',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_raw_config',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_security_groups',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_tags',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_userdata_file',
        ),
        migrations.RemoveField(
            model_name='poolconfiguration',
            name='ec2_userdata_macros',
        ),
        migrations.CreateModel(
            name='EC2Instance',
            fields=[
                ('instance_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                                                      parent_link=True, primary_key=True, serialize=False,
                                                      to='ec2spotmanager.Instance')),
                ('status_code', models.IntegerField()),
                ('status_data', models.CharField(blank=True, max_length=4095, null=True)),
                ('ec2_instance_id', models.CharField(blank=True, max_length=255, null=True)),
                ('ec2_region', models.CharField(max_length=255)),
                ('ec2_zone', models.CharField(max_length=255)),
            ],
            bases=('ec2spotmanager.instance',),
        ),
        migrations.CreateModel(
            name='EC2PoolConfiguration',
            fields=[
                ('poolconfiguration_ptr', models.OneToOneField(auto_created=True, parent_link=True,
                                                               primary_key=True, serialize=False,
                                                               on_delete=django.db.models.deletion.CASCADE,
                                                               to='ec2spotmanager.PoolConfiguration')),
                ('aws_access_key_id', models.CharField(blank=True, max_length=255, null=True)),
                ('aws_secret_access_key', models.CharField(blank=True, max_length=255, null=True)),
                ('ec2_key_name', models.CharField(blank=True, max_length=255, null=True)),
                ('ec2_security_groups', models.CharField(blank=True, max_length=255, null=True)),
                ('ec2_instance_types', models.CharField(blank=True, max_length=1023, null=True)),
                ('ec2_image_name', models.CharField(blank=True, max_length=255, null=True)),
                ('ec2_userdata_file', models.FileField(
                    storage=django.core.files.storage.FileSystemStorage(
                        location=b'/home/decoder/Mozilla/repos/FuzzManager/server'),
                    null=True, upload_to=ec2spotmanager.models.get_storage_path, blank=True)),
                ('ec2_userdata_macros', models.CharField(blank=True, max_length=4095, null=True)),
                ('ec2_allowed_regions', models.CharField(blank=True, max_length=1023, null=True)),
                ('ec2_max_price', models.DecimalField(blank=True, decimal_places=6, max_digits=12, null=True)),
                ('ec2_tags', models.CharField(blank=True, max_length=1023, null=True)),
                ('ec2_raw_config', models.CharField(blank=True, max_length=4095, null=True)),
            ],
            bases=('ec2spotmanager.poolconfiguration',),
        ),
        migrations.RunPython(restore_data, reverse_save_data),
    ]
