from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django.conf import settings
from django.forms import CharField, EmailField, ModelForm, Textarea, TextInput
from rest_framework.exceptions import ValidationError

from .models import BugzillaTemplate, User


class Row(Div):
    css_class = "row"


class BugzillaTemplateBugForm(ModelForm):
    class Meta:
        model = BugzillaTemplate
        fields = [
            "name",
            "summary",
            "product",
            "component",
            "whiteboard",
            "keywords",
            "op_sys",
            "platform",
            "cc",
            "assigned_to",
            "priority",
            "severity",
            "alias",
            "qa_contact",
            "version",
            "target_milestone",
            "attrs",
            "description",
            "security",
            "security_group",
            "testcase_filename",
            "blocks",
            "dependson",
        ]

        labels = {
            "name": "Template name",
            "summary": "Summary",
            "whiteboard": "Whiteboard",
            "keywords": "Keywords",
            'op_sys"': "OS",
            "platform": "Platform",
            "cc": "Cc",
            "assigned_to": "Assigned to",
            "priority": "Priority",
            "severity": "Severity",
            "alias": "Alias",
            "qa_contact": "QA",
            "version": "Version",
            "target_milestone": "Target milestone",
            "attrs": "Custom fields",
            "description": "Bug description",
            "security": "This is a security bug",
            "security_group": "Security group",
            "testcase_filename": "Filename that will be used for the testcase",
            "blocks": "Blocks",
            "dependson": "Depends On",
        }


class BugzillaTemplateCommentForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        HTML("""<div v-pre>"""),
        "name",
        "comment",
        Row(Field("testcase_filename", wrapper_class="col-md-6")),
        Submit("submit", "Save", css_class="btn btn-danger"),
        HTML(
            """<a href="{% url 'crashmanager:templates' %}" class="btn btn-default">"""
            """Cancel</a>"""
        ),
        HTML("""</div>"""),
    )

    class Meta:
        model = BugzillaTemplate
        fields = [
            "name",
            "comment",
            "testcase_filename",
        ]
        labels = {
            "name": "Template name",
            "comment": "Comment",
            "testcase_filename": "Filename that will be used for the testcase",
        }
        widgets = {
            "name": TextInput(),
            "comment": Textarea(attrs={"rows": 6}),
            "testcase_filename": TextInput(),
        }


class UserSettingsForm(ModelForm):
    email = EmailField(label="Email:")

    class Meta:
        model = User
        fields = [
            "defaultToolsFilter",
            "defaultProviderId",
            "defaultTemplateId",
            "bucket_hit",
            "coverage_drop",
            "inaccessible_bug",
            "tasks_failed",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance", None)
        if instance:
            self.initial["email"] = instance.user.email

        if not settings.ALLOW_EMAIL_EDITION:
            self.fields["email"].required = False
            self.fields["email"].widget.attrs["readonly"] = True

        self.fields["defaultToolsFilter"].required = False

    def clean_defaultToolsFilter(self):
        data = self.cleaned_data.get("defaultToolsFilter", None)
        if (
            self.user
            and list(self.user.defaultToolsFilter.all()) != list(data)
            and self.user.restricted
        ):
            raise ValidationError(
                "You don't have permission to change your tools filter."
            )
        return data

    def clean_defaultProviderId(self):
        data = self.cleaned_data["defaultProviderId"]
        return data

    def save(self, *args, **kwargs):
        self.instance.user.email = self.cleaned_data["email"]
        self.instance.user.save()
        return super().save(*args, **kwargs)
