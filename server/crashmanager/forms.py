from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Div, Field, Submit
from django.forms import CharField, ModelForm, Textarea, TextInput

from .models import BugzillaTemplate


class Row(Div):
    css_class = 'row'


class BugzillaTemplateBugForm(ModelForm):
    helper = FormHelper()
    helper.layout = Layout(
        Row(Field('name', wrapper_class='col-md-6')),
        'summary',
        Row(
            Field('product', wrapper_class='col-md-6'),
            Field('component', wrapper_class='col-md-6'),
        ),
        HTML("""<productcomponentselect></productcomponentselect>"""),
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
        HTML("""<a href="{% url 'crashmanager:templates' %}" class="btn btn-default">Cancel</a>""")
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
        'name',
        'comment',
        Submit('submit', 'Save', css_class='btn btn-danger'),
        HTML("""<a href="{% url 'crashmanager:templates' %}" class="btn btn-default">Cancel</a>""")
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
