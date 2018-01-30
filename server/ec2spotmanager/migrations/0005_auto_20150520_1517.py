# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import ec2spotmanager.models  # noqa


class Migration(migrations.Migration):

    dependencies = [
        ('ec2spotmanager', '0004_auto_20150507_1311'),
    ]

    operations = [
        migrations.CreateModel(
            name='PoolUptimeAccumulatedEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('accumulated_count', models.IntegerField(default=0)),
                ('uptime_percentage', models.DecimalField(null=True, max_digits=5, decimal_places=2, blank=True)),
                ('pool', models.ForeignKey(to='ec2spotmanager.InstancePool')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PoolUptimeDetailedEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('target', models.IntegerField()),
                ('actual', models.IntegerField()),
                ('pool', models.ForeignKey(to='ec2spotmanager.InstancePool')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
