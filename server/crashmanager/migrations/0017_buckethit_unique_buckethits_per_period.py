# Generated by Django 4.2.8 on 2024-12-04 22:06

from django.db import migrations, models


def fix_existing_buckethit_dupes(apps, schema_editor):
    BucketHit = apps.get_model("crashmanager", "BucketHit")

    counts = {}
    for key in BucketHit.objects.values_list("bucket_id", "tool_id", "begin"):
        counts.setdefault(key, 0)
        counts[key] += 1
    bad = {k: v for k, v in counts.items() if v > 1}
    for bid, tid, ts in bad:
        first, *rest = BucketHit.objects.filter(bucket_id=bid, tool_id=tid, begin=ts)
        first.count += sum(el.count for el in rest)
        first.save()
        for el in rest:
            el.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crashmanager", "0016_alter_crashentry_testcase"),
    ]

    operations = [
        migrations.RunPython(
            fix_existing_buckethit_dupes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="buckethit",
            constraint=models.UniqueConstraint(
                fields=("bucket", "tool", "begin"), name="unique_buckethits_per_period"
            ),
        ),
    ]
