# forms.py
import re

from django.conf import settings

import django.forms as forms
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import LayoutObject, Layout, Field, Submit, Row, Div, Fieldset
from crispy_forms.bootstrap import InlineRadios, InlineCheckboxes, UneditableField

from pyensemble.models import FormXQuestion, Question, Subject, Form, Experiment, ExperimentXForm, DataFormat

import pdb


class EnumCreateForm(forms.ModelForm):
    class Meta:
        model = DataFormat
        exclude = ('df_type',)

        widgets = {
            'enum_values': forms.TextInput(attrs={'placeholder':'e.g. "Yes","No"'})
        }

    def __init__(self,*args,**kwargs):
        super(EnumCreateForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = 'enum_create'
        self.helper.form_class = 'editor-form'

class QuestionEditHelper(FormHelper):
    form_method = 'POST'
    form_class = 'editor-form'

    layout = Layout(
        Div(
            Field('text'),
            Field('dfid'),
            Field('html_field_type'),
            css_class='text-left',
            ),
        )   

class QuestionCreateForm(forms.ModelForm):
    dfid = forms.ChoiceField(label='Response type', choices=())

    class Meta:
        model=Question
        exclude=('_unique_hash','forms','data_format','category','value_range','value_default','audio_path')

        widgets = {
            'text': forms.TextInput(attrs={'placeholder':'Enter the question text here'}),
            'html_field_type': forms.Select(attrs={'placeholder':'Choose a display format'}),
            'dfid': forms.Select(attrs={'placeholder':'Choose a response type'})
        }

    def __init__(self,*args,**kwargs):
        super(QuestionCreateForm, self).__init__(*args, **kwargs)

        # pdb.set_trace()
        self.fields['html_field_type'].label = 'Display format'

        # Generate choices for the data format
        self.fields['dfid'].choices=((dfid.pk,dfid.choice()) for dfid in DataFormat.objects.all())

        # Deal with form layout
        self.helper = QuestionEditHelper()
        self.helper.form_action = 'question_create'

class QuestionUpdateForm(QuestionCreateForm):
    def __init__(self,*args,**kwargs):
        super(QuestionUpdateForm,self).__init__(*args,**kwargs)

        self.helper = QuestionEditHelper()


# borrowed this from meamstream
class QuestionPresentForm(forms.ModelForm):
    # This is just a placeholder definition that has to be here so that the field is found. The choices are actually populated at the time that the form is rendered via the __init__ function
    option = forms.ChoiceField(widget=forms.RadioSelect, choices=())

    class Meta:
        model = Question
        fields = ['option']

    def __init__(self, *args, **kwargs):
        super(QuestionPresentForm, self).__init__(*args, **kwargs)

        # Set the label of the input element to the question_text
        # self.fields['option'].label = self.instance.text

        use_crispy = True
        field_params = {
            'label': self.instance.text,
            'required': True,
            }

        # Set up the input field as a function of the HTML type
        html_field_type = self.instance.html_field_type

        # If a field type hasn't been specified, choose radiogroup as a default
        if not html_field_type:
            html_field_type = 'radiogroup'

        if html_field_type in ['radiogroup', 'checkbox','menu']:
            # Deal with getting our choices
            field_params['choices'] = self.instance.choices()

            if html_field_type == 'radiogroup':
                widget = forms.RadioSelect
                
            elif html_field_type == 'checkbox':
                widget = forms.CheckboxSelectMultiple

            elif html_field_type == 'menu':
                widget = forms.Select

        elif re.match('numeric',html_field_type):
            widget = forms.NumberInput

        elif html_field_type == 'text':
            widget = forms.TextInput

        elif html_field_type == 'textarea':
            widget = forms.Textarea

        field_params['widget'] = widget

        if html_field_type in ['radiogroup','menu']:
            self.fields['option'] = forms.ChoiceField(**field_params)
        elif html_field_type == 'checkbox':
            self.fields['option'] = forms.MultipleChoiceField(**field_params)
        elif html_field_type == 'numeric':
            self.fields['option'] = forms.IntegerField(**field_params)
        else:
            self.fields['option'] = forms.CharField(**field_params)


QuestionModelFormSet = forms.modelformset_factory(Question, form=QuestionPresentForm, extra=0, max_num=1)

class QuestionModelFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(QuestionModelFormSetHelper, self).__init__(*args, **kwargs)

        self.form_method='post'  

class FormQuestionForm(forms.ModelForm):
    class Meta:
        model = FormXQuestion
        exclude = ('form_question_num','question_iteration',)

class FormForm(forms.ModelForm):
    class Meta:
        model = Form
        exclude = ('version','category','header_audio_path','footer_audio_path','questions','experiments')

    def __init__(self, *args, **kwargs):
        super(FormForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.template = 'pyensemble/partly_crispy/formquestion_formset.html'
        self.helper.formset_tag = True
        self.helper.formset_method = 'POST'

    field_order = ('name','header','footer','visit_once','locked')

FormQuestionFormset = forms.inlineformset_factory(Form, FormXQuestion, 
    form=FormQuestionForm, 
    fields=('form_question_num','required'), 
    can_order=True,
    can_delete=True,
    extra=0,
    )

class ExperimentFormForm(forms.ModelForm):
    class Meta:
        model = ExperimentXForm
        exclude = ('form_order',)

    field_order = ('form_handler','condition_script','stimulus_script','goto','repeat','break_loop_button','break_loop_button_text','continue_button_text')


class ExperimentForm(forms.ModelForm):
    class Meta:
        model=Experiment
        exclude = ('language','play_question_audio','params','locked','forms')

    def __init__(self, *args, **kwargs):
        super(ExperimentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.template = 'pyensemble/partly_crispy/experimentform_formset.html'
        self.helper.formset_tag = True
        self.helper.formset_method = 'POST'

ExperimentFormFormset = forms.inlineformset_factory(Experiment, ExperimentXForm, 
    form=ExperimentFormForm, 
    fields=('form_order', 'form_handler', 'goto','repeat','condition_script','stimulus_script', 'break_loop_button', 'break_loop_button_text', 'continue_button_text'), 
    can_order=True,
    can_delete=True,
    extra=0,
    )

class TicketCreationForm(forms.Form):
    input_format = '%d/%m/%Y %H:00'
    num_master = forms.IntegerField(label='Number of (multiple-use) master tickets', initial=0)
    master_expiration = forms.DateTimeField(required=False, initial=None,  input_formats=[input_format])

    num_user = forms.IntegerField(label='Number of (single-use) user tickets', initial=0)
    user_expiration = forms.DateTimeField(required=False, initial=(timezone.now() + timezone.timedelta(weeks=1)).strftime(input_format), input_formats=[input_format])

    experiment_id = forms.IntegerField(widget=forms.HiddenInput())

    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_action = 'create_ticket'
    helper.form_id = 'ticketCreateForm'

class RegisterSubjectForm(forms.ModelForm):

    class Meta:
        model = Subject
        fields = ('name_first','name_last','dob','sex','race','ethnicity')
        field_classes = {
            # Need to make dob a date field, because right now it is encrypted and not showing as such
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
