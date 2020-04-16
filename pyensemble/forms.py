# forms.py
import re

import django.forms as forms
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from crispy_forms.bootstrap import InlineRadios, InlineCheckboxes

from pyensemble.models import FormXQuestion, Question, Subject, Form

import pdb

# class FormModelForm(forms.ModelForm):
#     class Meta:
#         model = Form

# borrowed this from meamstream
class QuestionModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuestionModelForm, self).__init__(*args, **kwargs)

        use_crispy = True
        field_params = {'required': False}

        # Set up the input field as a function of the HTML type
        html_field_type = self.instance.questionxdataformat_set.get().html_field_type

        if html_field_type in ['radiogroup', 'checkbox','menu']:
            # Deal with getting our choices
            enum_value_str = self.instance.values.all().values_list('enum_values',flat=True)[0]
            field_params['choices'] = [(val,lbl) for val,lbl in enumerate(enum_value_str.replace('"','').replace('\\','').split(','))]

            # pdb.set_trace()
            if html_field_type == 'radiogroup':
                widget = forms.RadioSelect
                
            elif html_field_type == 'checkbox':
                widget = forms.CheckboxSelectMultiple

            elif html_field_type == 'menu':
                widget = forms.Select

        elif re.match('^int',html_field_type):
            widget = forms.NumberInput

        elif html_field_type == 'text':
            widget = forms.TextInput

        elif html_field_type == 'textarea':
            widget = forms.TextArea

        field_params['widget'] = widget


        self.fields['option'] = forms.ChoiceField(**field_params)
        # self.fields['stimulus'] = forms.HiddenInput()

        if use_crispy:
            # Access to crispy forms
            self.helper = FormHelper()
            self.helper.field_class='row justify-content-center'
            self.form_tag = False

            if html_field_type == 'radiogroup':
                self.helper.layout = Layout(
                    InlineRadios('option',template="pyensemble/crispy_overrides/radioselect_inline.html"),
                    )
            elif html_field_type == 'checkbox':
                self.helper.layout = Layout(
                    InlineCheckboxes('option',template="pyensemble/crispy_overrides/checkboxselectmultiple_inline.html"),
                    )

            # pdb.set_trace()
            self.helper.render_required_fields = True                

        # Set the label of the input element to the question_text
        self.fields['option'].label = self.instance.question_text

    # This is just a placeholder definition that has to be here so that the field is found. The choices are actually populated at the time that the form is rendered via the __init__ function
    option = forms.ChoiceField(widget=forms.RadioSelect, choices=())
    # stimulus = forms.IntegerField()

    class Meta:
        model = Question
        fields = ['option']

class QuestionModelFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(QuestionModelFormSetHelper, self).__init__(*args, **kwargs)

        self.form_method='post'  

class TicketCreationForm(forms.Form):
    input_format = '%d/%m/%Y %H:00'
    num_master = forms.IntegerField(label='Number of (multiple-use) master tickets', initial=0)
    master_expiration = forms.DateTimeField(required=False, initial=None,  input_formats=[input_format])

    num_user = forms.IntegerField(label='Number of (single-use) user tickets', initial=0)
    user_expiration = forms.DateTimeField(required=False, initial=(timezone.now() + timezone.timedelta(weeks=1)).strftime(input_format), input_formats=[input_format])

    experiment_id = forms.IntegerField(widget=forms.HiddenInput())

    helper = FormHelper()
    helper.add_input(Submit('submit', 'Create Ticket(s)', css_class='btn-primary contentlist-item-link'))
    helper.form_method = 'POST'
    helper.form_action = 'create_ticket'

class RegisterSubjectForm(forms.ModelForm):
    # Need to make dob a date field, because right now it is encrypted and not showing as such
    # dob = forms.DateField()
    class Meta:
        model = Subject
        fields = ('name_first','name_last','dob','sex','race','ethnicity')
        field_classes = {
            'dob': forms.DateField,
        }
        labels = {
            "name_first": "First name",
            "name_last": "Last name",
            "dob": "Date of birth",
            "sex": "Biological sex",
            "ethnicity": "Ethnicity",
            "race": "Race",
        }
        widgets = {
            'dob': forms.DateInput(attrs={'placeholder':'MM/DD/YYYY'}),
        }
