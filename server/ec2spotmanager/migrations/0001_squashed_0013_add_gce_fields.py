# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-12-09 00:08

from __future__ import annotations

import django.core.files.storage
from django.db import migrations, models
import django.db.migrations.operations.special
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone
import ec2spotmanager.models


class Migration(migrations.Migration):

    replaces = [
        ("ec2spotmanager", "0001_initial"),
        ("ec2spotmanager", "0002_instancestatusentry_poolstatusentry"),
        ("ec2spotmanager", "0003_auto_20150505_1225"),
        ("ec2spotmanager", "0004_auto_20150507_1311"),
        ("ec2spotmanager", "0005_auto_20150520_1517"),
        ("ec2spotmanager", "0006_auto_20150625_2050"),
        ("ec2spotmanager", "0007_instance_type_to_list"),
        ("ec2spotmanager", "0008_remove_aws_creds"),
        ("ec2spotmanager", "0009_add_instance_size"),
        ("ec2spotmanager", "0010_extend_instance_types"),
        ("ec2spotmanager", "0011_auto_20181012_0011"),
        ("ec2spotmanager", "0012_add_instance_provider"),
        ("ec2spotmanager", "0013_add_gce_fields"),
    ]

    initial = True

    dependencies: list[str] = []

    operations = [
        migrations.CreateModel(
            name="Instance",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("hostname", models.CharField(blank=True, max_length=255, null=True)),
                ("status_code", models.IntegerField()),
                (
                    "status_data",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "ec2_instance_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("ec2_region", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="InstancePool",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("last_cycled", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="PoolConfiguration",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("size", models.IntegerField(blank=True, default=1, null=True)),
                (
                    "cycle_interval",
                    models.IntegerField(blank=True, default=86400, null=True),
                ),
                (
                    "aws_access_key_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "aws_secret_access_key",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "ec2_key_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "ec2_security_groups",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "ec2_instance_type",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "ec2_image_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "ec2_userdata_file",
                    models.FileField(
                        blank=True,
                        null=True,
                        storage=django.core.files.storage.FileSystemStorage(
                            location=getattr(settings, 'USERDATA_STORAGE', None)
                        ),
                        upload_to=ec2spotmanager.models.get_storage_path,
                    ),
                ),
                (
                    "ec2_userdata_macros",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "ec2_allowed_regions",
                    models.CharField(blank=True, max_length=1023, null=True),
                ),
                (
                    "ec2_max_price",
                    models.DecimalField(
                        blank=True, decimal_places=6, max_digits=12, null=True
                    ),
                ),
                ("ec2_tags", models.CharField(blank=True, max_length=1023, null=True)),
                (
                    "ec2_raw_config",
                    models.TextField(blank=True, null=True),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ec2spotmanager.PoolConfiguration",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="instancepool",
            name="config",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="ec2spotmanager.PoolConfiguration",
            ),
        ),
        migrations.AddField(
            model_name="instance",
            name="pool",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="ec2spotmanager.InstancePool",
            ),
        ),
        migrations.CreateModel(
            name="InstanceStatusEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("msg", models.CharField(max_length=4095)),
                (
                    "instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ec2spotmanager.Instance",
                    ),
                ),
                ("isCritical", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="PoolStatusEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("msg", models.CharField(max_length=4095)),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ec2spotmanager.InstancePool",
                    ),
                ),
                ("isCritical", models.BooleanField(default=False)),
                ("type", models.IntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name="instancepool",
            name="isEnabled",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="PoolUptimeAccumulatedEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("accumulated_count", models.IntegerField(default=0)),
                (
                    "uptime_percentage",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ec2spotmanager.InstancePool",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PoolUptimeDetailedEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("target", models.IntegerField()),
                ("actual", models.IntegerField()),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ec2spotmanager.InstancePool",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="instance",
            name="ec2_zone",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name="poolconfiguration",
            old_name="ec2_instance_type",
            new_name="ec2_instance_types",
        ),
        migrations.RemoveField(
            model_name="poolconfiguration", name="aws_access_key_id",
        ),
        migrations.RemoveField(
            model_name="poolconfiguration", name="aws_secret_access_key",
        ),
        migrations.AddField(
            model_name="instance", name="size", field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="poolconfiguration",
            name="ec2_instance_types",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RenameField(
            model_name="instance", old_name="ec2_instance_id", new_name="instance_id",
        ),
        migrations.RenameField(
            model_name="instance", old_name="ec2_region", new_name="region",
        ),
        migrations.RenameField(
            model_name="instance", old_name="ec2_zone", new_name="zone",
        ),
        migrations.RenameField(
            model_name="poolconfiguration",
            old_name="ec2_userdata_macros",
            new_name="ec2_userdata_macros",
        ),
        migrations.RenameField(
            model_name="poolconfiguration",
            old_name="ec2_userdata_file",
            new_name="ec2_userdata_file",
        ),
        migrations.CreateModel(
            name="ProviderStatusEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("provider", models.CharField(max_length=255)),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                ("type", models.IntegerField()),
                ("msg", models.CharField(max_length=4095)),
                ("isCritical", models.BooleanField(default=False)),
            ],
        ),
        migrations.AddField(
            model_name="instance",
            name="provider",
            field=models.CharField(default="EC2Spot", max_length=255),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name="poolconfiguration",
            old_name="ec2_tags",
            new_name="instance_tags",
        ),
        migrations.RenameField(
            model_name="poolconfiguration",
            old_name="ec2_max_price",
            new_name="max_price",
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_args",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_cmd",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_container_name",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_disk_size",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_docker_privileged",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_env",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_env_include_macros",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_image_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_machine_types",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="poolconfiguration",
            name="gce_raw_config",
            field=models.TextField(blank=True, null=True),
        ),
    ]
