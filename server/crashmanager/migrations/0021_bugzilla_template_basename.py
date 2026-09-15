from django.db import migrations


def strip_template_extensions(apps, schema_editor):
    Template = apps.get_model("crashmanager", "BugzillaTemplate")
    templates = Template.objects.using(schema_editor.connection.alias)
    for template in templates.exclude(testcase_filename="").iterator():
        filename = template.testcase_filename
        if "." in filename:
            templates.filter(pk=template.pk).update(
                testcase_filename=filename.rsplit(".", 1)[0]
            )


class Migration(migrations.Migration):
    dependencies = [
        ("crashmanager", "0020_alter_bucket_optimizedsignature_and_more"),
    ]

    operations = [migrations.RunPython(strip_template_extensions)]
