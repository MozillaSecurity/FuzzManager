# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
from crashmanager.models import Tool  # noqa


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crashmanager', '0004_add_tool'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('defaultTemplateId', models.IntegerField(default=0)),
                ('defaultToolsFilter', models.ManyToManyField(to='crashmanager.Tool')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='crashentry',
            name='tool',
            field=models.ForeignKey(default=1, to='crashmanager.Tool'),
            preserve_default=False,
        ),
    ]
