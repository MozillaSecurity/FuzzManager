# Generated by Django 4.1.5 on 2023-01-25 18:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crashmanager", "0008_user_tasks_failed"),
    ]

    operations = [
        migrations.AddField(
            model_name="bucket",
            name="doNotReduce",
            field=models.BooleanField(default=False),
        ),
    ]
