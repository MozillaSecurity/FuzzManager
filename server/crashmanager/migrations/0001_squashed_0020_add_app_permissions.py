# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-12-09 00:06
from __future__ import unicode_literals

from django.conf import settings
import django.core.files.storage
from django.db import migrations, models
import django.db.migrations.operations.special
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    replaces = [
        ("crashmanager", "0001_initial"),
        ("crashmanager", "0002_bugzillatemplate_security"),
        ("crashmanager", "0003_bucket_frequent"),
        ("crashmanager", "0004_add_tool"),
        ("crashmanager", "0005_add_user"),
        ("crashmanager", "0006_user_defaultproviderid"),
        ("crashmanager", "0007_bugzillatemplate_comment"),
        ("crashmanager", "0008_crashentry_crashaddressnumeric"),
        ("crashmanager", "0009_copy_crashaddress"),
        ("crashmanager", "0010_bugzillatemplate_security_group"),
        ("crashmanager", "0011_bucket_permanent"),
        ("crashmanager", "0012_crashentry_cachedcrashinfo"),
        ("crashmanager", "0013_init_cachedcrashinfo"),
        ("crashmanager", "0014_bugzillatemplate_testcase_filename"),
        ("crashmanager", "0015_crashentry_triagedonce"),
        ("crashmanager", "0016_auto_20160308_1500"),
        ("crashmanager", "0017_user_restricted"),
        ("crashmanager", "0018_auto_20170620_1503"),
        ("crashmanager", "0019_bucket_optimizedsignature"),
        ("crashmanager", "0020_add_app_permissions"),
    ]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Bucket",
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
                ("signature", models.TextField()),
                ("shortDescription", models.CharField(blank=True, max_length=1023)),
            ],
        ),
        migrations.CreateModel(
            name="Bug",
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
                ("externalId", models.CharField(blank=True, max_length=255)),
                ("closed", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="BugProvider",
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
                ("classname", models.CharField(max_length=255)),
                ("hostname", models.CharField(max_length=255)),
                ("urlTemplate", models.CharField(max_length=1023)),
            ],
        ),
        migrations.CreateModel(
            name="BugzillaTemplate",
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
                ("name", models.TextField()),
                ("product", models.TextField()),
                ("component", models.TextField()),
                ("summary", models.TextField(blank=True)),
                ("version", models.TextField()),
                ("description", models.TextField(blank=True)),
                ("whiteboard", models.TextField(blank=True)),
                ("keywords", models.TextField(blank=True)),
                ("op_sys", models.TextField(blank=True)),
                ("platform", models.TextField(blank=True)),
                ("priority", models.TextField(blank=True)),
                ("severity", models.TextField(blank=True)),
                ("alias", models.TextField(blank=True)),
                ("cc", models.TextField(blank=True)),
                ("assigned_to", models.TextField(blank=True)),
                ("qa_contact", models.TextField(blank=True)),
                ("target_milestone", models.TextField(blank=True)),
                ("attrs", models.TextField(blank=True)),
                ("security", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Client",
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
            ],
        ),
        migrations.CreateModel(
            name="CrashEntry",
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
                ("rawStdout", models.TextField(blank=True)),
                ("rawStderr", models.TextField(blank=True)),
                ("rawCrashData", models.TextField(blank=True)),
                ("metadata", models.TextField(blank=True)),
                ("env", models.TextField(blank=True)),
                ("args", models.TextField(blank=True)),
                ("crashAddress", models.CharField(blank=True, max_length=255)),
                ("shortSignature", models.CharField(blank=True, max_length=255)),
                (
                    "bucket",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="crashmanager.Bucket",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="crashmanager.Client",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="OS",
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
                ("name", models.CharField(max_length=63)),
                ("version", models.CharField(blank=True, max_length=127, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Platform",
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
                ("name", models.CharField(max_length=63)),
            ],
        ),
        migrations.CreateModel(
            name="Product",
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
                ("name", models.CharField(max_length=63)),
                ("version", models.CharField(blank=True, max_length=127, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="TestCase",
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
                (
                    "test",
                    models.FileField(
                        storage=django.core.files.storage.FileSystemStorage(
                            location=None
                        ),
                        upload_to=b"tests",
                    ),
                ),
                ("size", models.IntegerField(default=0)),
                ("quality", models.IntegerField(default=0)),
                ("isBinary", models.BooleanField(default=False)),
            ],
        ),
        migrations.AddField(
            model_name="crashentry",
            name="os",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="crashmanager.OS"
            ),
        ),
        migrations.AddField(
            model_name="crashentry",
            name="platform",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="crashmanager.Platform"
            ),
        ),
        migrations.AddField(
            model_name="crashentry",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="crashmanager.Product"
            ),
        ),
        migrations.AddField(
            model_name="crashentry",
            name="testcase",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="crashmanager.TestCase",
            ),
        ),
        migrations.AddField(
            model_name="bug",
            name="externalType",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="crashmanager.BugProvider",
            ),
        ),
        migrations.AddField(
            model_name="bucket",
            name="bug",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="crashmanager.Bug",
            ),
        ),
        migrations.AddField(
            model_name="bucket",
            name="frequent",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="Tool",
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
                ("name", models.CharField(max_length=63)),
            ],
        ),
        migrations.CreateModel(
            name="User",
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
                ("defaultTemplateId", models.IntegerField(default=0)),
                ("defaultToolsFilter", models.ManyToManyField(to="crashmanager.Tool")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("defaultProviderId", models.IntegerField(default=1)),
            ],
        ),
        migrations.AddField(
            model_name="crashentry",
            name="tool",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="crashmanager.Tool",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="bugzillatemplate",
            name="comment",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="crashentry",
            name="crashAddressNumeric",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bugzillatemplate",
            name="security_group",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="bucket",
            name="permanent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="crashentry",
            name="cachedCrashInfo",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bugzillatemplate",
            name="testcase_filename",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="crashentry",
            name="triagedOnce",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="restricted",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="BucketWatch",
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
                ("lastCrash", models.IntegerField(default=0)),
                (
                    "bucket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="crashmanager.Bucket",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="crashmanager.User",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="user",
            name="bucketsWatching",
            field=models.ManyToManyField(
                through="crashmanager.BucketWatch", to="crashmanager.Bucket"
            ),
        ),
        migrations.AddField(
            model_name="bucket",
            name="optimizedSignature",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": (
                    ("view_crashmanager", "Can see CrashManager app"),
                    ("view_covmanager", "Can see CovManager app"),
                    ("view_ec2spotmanager", "Can see EC2SpotManager app"),
                )
            },
        ),
    ]
