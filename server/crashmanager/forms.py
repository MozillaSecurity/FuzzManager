from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django.conf import settings
from django.forms import EmailField, ModelForm, Textarea, TextInput

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
    email = EmailField(label="Email:", disabled=not settings.ALLOW_EMAIL_EDITION)

    class Meta:
        model = User
        fields = (
            "defaultToolsFilter",
            "defaultProviderId",
            "defaultTemplateId",
            "bucket_hit",
            "coverage_drop",
            "inaccessible_bug",
            "tasks_failed",
        )

    def __init__(self, *args, **kwargs):
        instance = kwargs["instance"]
        kwargs.setdefault("initial", {})["email"] = instance.user.email
        super().__init__(*args, **kwargs)
        self.fields["defaultToolsFilter"].disabled = instance.restricted
        self.fields["defaultToolsFilter"].required = False

    def save(self, *args, **kwargs):
        if settings.ALLOW_EMAIL_EDITION:
            self.instance.user.email = self.cleaned_data["email"]
            self.instance.user.save()
        return super().save(*args, **kwargs)
