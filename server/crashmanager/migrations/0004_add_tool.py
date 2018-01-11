# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


def create_migration_tool(apps, schema_editor):
    Tool = apps.get_model("crashmanager", "Tool")
    db_alias = schema_editor.connection.alias
    Tool.objects.using(db_alias).bulk_create([
        Tool(name="migrated"),
    ])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crashmanager', '0003_bucket_frequent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tool',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=63)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(
            create_migration_tool,
        ),
    ]
