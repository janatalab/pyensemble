# forms.py

import django.forms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from crispy_forms.bootstrap import InlineRadios, InlineCheckboxes

from pyensemble.models import FormXQuestion, Question, Subject

import pdb

# borrowed this from meamstream
class QuestionModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuestionModelForm, self).__init__(*args, **kwargs)

        use_crispy = True

        # Access to crispy forms
        self.helper = FormHelper()
        self.helper.field_class='row justify-content-center'
        self.form_tag = False

        # Set up the input field as a function of the HTML type
        html_field_type = self.instance.questionxdataformat_set.get().html_field_type
        if html_field_type in ['radiogroup', 'checkbox']:
            enum_value_str = self.instance.values.all().values_list('enum_values',flat=True)[0]

            choices = [(val,lbl) for val,lbl in enumerate(enum_value_str.replace('"','').replace('\\','').split(','))]
            # pdb.set_trace()
            if html_field_type == 'radiogroup':
                widget = forms.RadioSelect
                
            elif html_field_type == 'checkbox':
                widget = forms.CheckboxSelectMultiple

            self.fields['option'] = forms.ChoiceField(
                widget= widget, 
                choices= choices,
                required= False,
            )

            if use_crispy:
                if html_field_type == 'radiogroup':
                    self.helper.layout = Layout(
                        InlineRadios('option',template="pyensemble/crispy_overrides/radioselect_inline.html"),
                        )
                elif html_field_type == 'checkbox':
                    self.helper.layout = Layout(
                        InlineCheckboxes('option',template="pyensemble/crispy_overrides/checkboxselectmultiple_inline.html"),
                        )                    

        # Set the label of the input element to the question_text
        self.fields['option'].label = self.instance.question_text

    # This is just a placeholder definition that has to be here so that the field is found. The choices are actually populated at the time that the form is rendered via the __init__ function
    option = forms.ChoiceField(widget=forms.RadioSelect, choices=())

    class Meta:
        model = Question
        fields = ['option']

class QuestionModelFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(QuestionModelFormHelper, self).__init__(*args, **kwargs)

        self.form_method='post'  

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
