# Generated by Django 4.2.13 on 2024-09-09 21:27

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crashmanager", "0017_remove_user_coverage_drop"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="tasks_failed",
        ),
    ]
