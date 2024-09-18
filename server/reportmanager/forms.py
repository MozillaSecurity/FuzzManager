# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django.conf import settings
from django.forms import (
    CharField,
    ChoiceField,
    EmailField,
    ModelChoiceField,
    ModelForm,
    Textarea,
    TextInput,
)

from .models import BugProvider, BugzillaTemplate, User


class Row(Div):
    css_class = "row"


class BugzillaTemplateBugForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        HTML("""<div v-pre>"""),
        Row(Field("name", wrapper_class="col-md-6")),
        "summary",
        Row(
            Field("product", wrapper_class="col-md-6"),
            Field("component", wrapper_class="col-md-6"),
        ),
        HTML("""</div>"""),
        HTML("""<ppcselect></ppcselect>"""),
        HTML("""<div v-pre>"""),
        Row(
            Field("whiteboard", wrapper_class="col-md-6"),
            Field("keywords", wrapper_class="col-md-6"),
        ),
        Row(
            Field("op_sys", wrapper_class="col-md-6"),
            Field("platform", wrapper_class="col-md-6"),
        ),
        Row(
            Field("cc", wrapper_class="col-md-6"),
            Field("assigned_to", wrapper_class="col-md-6"),
        ),
        Row(
            Field("priority", wrapper_class="col-md-6"),
            Field("severity", wrapper_class="col-md-6"),
        ),
        Row(
            Field("alias", wrapper_class="col-md-6"),
            Field("qa_contact", wrapper_class="col-md-6"),
        ),
        Row(
            Field("version", wrapper_class="col-md-6"),
            Field("target_milestone", wrapper_class="col-md-6"),
        ),
        Row(
            Field("blocks", wrapper_class="col-md-6"),
            Field("dependson", wrapper_class="col-md-6"),
        ),
        "attrs",
        "description",
        "security",
        Row(Field("security_group", wrapper_class="col-md-6")),
        Submit("submit", "Save", css_class="btn btn-danger"),
        HTML(
            """<a href="{% url 'reportmanager:templates' %}" class="btn btn-default">"""
            """Cancel</a>"""
        ),
        HTML("""</div>"""),
    )
    product = CharField(
        label="Current product (choose below)",
        widget=TextInput(attrs={"disabled": True}),
    )
    component = CharField(
        label="Current component (choose below)",
        widget=TextInput(attrs={"disabled": True}),
    )

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
            "blocks": "Blocks",
            "dependson": "Depends On",
        }

        widgets = {}
        for field in fields:
            if field not in ["description", "attrs", "security"]:
                widgets[field] = TextInput()

        widgets["attrs"] = Textarea(attrs={"rows": 2})


class BugzillaTemplateCommentForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        HTML("""<div v-pre>"""),
        "name",
        "comment",
        Submit("submit", "Save", css_class="btn btn-danger"),
        HTML(
            """<a href="{% url 'reportmanager:templates' %}" class="btn btn-default">"""
            """Cancel</a>"""
        ),
        HTML("""</div>"""),
    )

    class Meta:
        model = BugzillaTemplate
        fields = [
            "name",
            "comment",
        ]
        labels = {
            "name": "Template name",
            "comment": "Comment",
        }
        widgets = {
            "name": TextInput(),
            "comment": Textarea(attrs={"rows": 6}),
        }


class UserSettingsForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Row(
            Field("default_provider_id", wrapper_class="col-md-6"),
            Field("default_template_id", wrapper_class="col-md-6"),
        ),
        "email",
        HTML("""<p><strong>Subscribe to notifications:</strong></p>"""),
        "inaccessible_bug",
        Submit("submit", "Save settings", css_class="btn btn-danger"),
    )
    default_provider_id = ModelChoiceField(
        queryset=BugProvider.objects.all(), label="Default Provider:", empty_label=None
    )
    default_template_id = ChoiceField(label="Default Template:")
    email = EmailField(label="Email:")

    class Meta:
        model = User
        fields = [
            "default_provider_id",
            "default_template_id",
            "inaccessible_bug",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["default_template_id"].choices = list(
            dict.fromkeys(
                [
                    (t.pk, f"{p.classname}: {t}")
                    for p in BugProvider.objects.all()
                    for t in p.get_instance().get_template_list()
                ]
            )
        )

        instance = kwargs.get("instance", None)
        if instance:
            self.initial["email"] = instance.user.email

        if not settings.ALLOW_EMAIL_EDITION:
            self.fields["email"].required = False
            self.fields["email"].widget.attrs["readonly"] = True

    def clean_default_provider_id(self):
        data = self.cleaned_data["default_provider_id"].id
        return data

    def save(self, *args, **kwargs):
        self.instance.user.email = self.cleaned_data["email"]
        self.instance.user.save()
        return super().save(*args, **kwargs)
