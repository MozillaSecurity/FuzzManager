from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Div, Field, Submit
from django.conf import settings
from django.forms import CharField, CheckboxSelectMultiple, ChoiceField, ModelChoiceField, \
    ModelMultipleChoiceField, ModelForm, Textarea, TextInput
from rest_framework.exceptions import ValidationError

from .models import BugProvider, BugzillaTemplate, Tool, User


class Row(Div):
    css_class = 'row'


class BugzillaTemplateBugForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        HTML("""<div v-pre>"""),
        Row(Field('name', wrapper_class='col-md-6')),
        'summary',
        Row(
            Field('product', wrapper_class='col-md-6'),
            Field('component', wrapper_class='col-md-6'),
        ),
        HTML("""</div>"""),
        HTML("""<ppcselect></ppcselect>"""),
        HTML("""<div v-pre>"""),
        Row(
            Field('whiteboard', wrapper_class='col-md-6'),
            Field('keywords', wrapper_class='col-md-6'),
        ),
        Row(
            Field('op_sys', wrapper_class='col-md-6'),
            Field('platform', wrapper_class='col-md-6'),
        ),
        Row(
            Field('cc', wrapper_class='col-md-6'),
            Field('assigned_to', wrapper_class='col-md-6'),
        ),
        Row(
            Field('priority', wrapper_class='col-md-6'),
            Field('severity', wrapper_class='col-md-6'),
        ),
        Row(
            Field('alias', wrapper_class='col-md-6'),
            Field('qa_contact', wrapper_class='col-md-6'),
        ),
        Row(
            Field('version', wrapper_class='col-md-6'),
            Field('target_milestone', wrapper_class='col-md-6'),
        ),
        'attrs',
        'description',
        'security',
        Row(Field('security_group', wrapper_class='col-md-6')),
        Row(Field('testcase_filename', wrapper_class='col-md-6')),
        Submit('submit', 'Save', css_class='btn btn-danger'),
        HTML("""<a href="{% url 'crashmanager:templates' %}" class="btn btn-default">Cancel</a>"""),
        HTML("""</div>""")
    )
    product = CharField(label='Current product (choose below)', widget=TextInput(attrs={'disabled': True}))
    component = CharField(label='Current component (choose below)', widget=TextInput(attrs={'disabled': True}))

    class Meta:
        model = BugzillaTemplate
        fields = [
            'name',
            'summary',
            'product',
            'component',
            'whiteboard',
            'keywords',
            'op_sys',
            'platform',
            'cc',
            'assigned_to',
            'priority',
            'severity',
            'alias',
            'qa_contact',
            'version',
            'target_milestone',
            'attrs',
            'description',
            'security',
            'security_group',
            'testcase_filename',
        ]

        labels = {
            'name': 'Template name',
            'summary': 'Summary',
            'whiteboard': 'Whiteboard',
            'keywords': 'Keywords',
            'op_sys"': 'OS',
            'platform': 'Platform',
            'cc': 'Cc',
            'assigned_to': 'Assigned to',
            'priority': 'Priority',
            'severity': 'Severity',
            'alias': 'Alias',
            'qa_contact': 'QA',
            'version': 'Version',
            'target_milestone': 'Target milestone',
            'attrs': 'Custom fields',
            'description': 'Bug description',
            'security': 'This is a security bug',
            'security_group': 'Security group',
            'testcase_filename': 'Filename that will be used for the testcase',
        }

        widgets = {}
        for field in fields:
            if field not in ['description', 'attrs', 'security']:
                widgets[field] = TextInput()

        widgets['attrs'] = Textarea(attrs={'rows': 2})


class BugzillaTemplateCommentForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        HTML("""<div v-pre>"""),
        'name',
        'comment',
        Submit('submit', 'Save', css_class='btn btn-danger'),
        HTML("""<a href="{% url 'crashmanager:templates' %}" class="btn btn-default">Cancel</a>"""),
        HTML("""</div>""")
    )

    class Meta:
        model = BugzillaTemplate
        fields = ['name', 'comment']
        labels = {
            'name': 'Template name',
            'comment': 'Comment',
        }
        widgets = {
            'name': TextInput(),
            'comment': Textarea(attrs={'rows': 6})
        }


class UserSettingsForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        'defaultToolsFilter',
        Row(
            Field('defaultProviderId', wrapper_class='col-md-6'),
            Field('defaultTemplateId', wrapper_class='col-md-6'),
        ),
        'email',
        Submit('submit', 'Save settings', css_class='btn btn-danger'),
    )
    defaultToolsFilter = ModelMultipleChoiceField(
        queryset=Tool.objects.all(),
        label='Select the tools you would like to include in your default views:',
        widget=CheckboxSelectMultiple(),
        required=False
    )
    defaultProviderId = ModelChoiceField(
        queryset=BugProvider.objects.all(),
        label='Default Provider:',
        empty_label=None
    )
    defaultTemplateId = ChoiceField(label='Default Template:')
    email = CharField(label='Email:')

    class Meta:
        model = User
        fields = ['defaultToolsFilter', 'defaultProviderId', 'defaultTemplateId']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['defaultTemplateId'].choices = list(dict.fromkeys([
            (t.pk, f"{p.classname}: {t}")
            for p in BugProvider.objects.all()
            for t in p.getInstance().getTemplateList()
        ]))

        instance = kwargs.get('instance', None)
        if instance:
            self.initial['email'] = instance.user.email

        if not settings.ALLOW_EMAIL_EDITION:
            self.fields['email'].required = False
            self.fields['email'].widget.attrs['readonly'] = True

    def clean_defaultToolsFilter(self):
        data = self.cleaned_data['defaultToolsFilter']
        if self.user and list(self.user.defaultToolsFilter.all()) != list(data) and self.user.restricted:
            raise ValidationError("You don't have permission to change your tools filter.")
        return data

    def clean_defaultProviderId(self):
        data = self.cleaned_data['defaultProviderId'].id
        return data

    def save(self, *args, **kwargs):
        self.instance.user.email = self.cleaned_data['email']
        self.instance.user.save()
        return super().save(*args, **kwargs)
