# forms.py
import re

from django.conf import settings

import django.forms as forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse

from crispy_forms.helper import FormHelper
from crispy_forms.layout import LayoutObject, Layout, Field, Submit, Row, Div, Fieldset
from crispy_forms.bootstrap import InlineRadios, InlineCheckboxes, UneditableField

from django_recaptcha.fields import ReCaptchaField

from pyensemble.models import FormXQuestion, Question, Subject, Form, Experiment, ExperimentXForm, DataFormat, Ticket, Study, Response, SessionFile

from pyensemble.widgets import RangeInput

import pdb

class EnumCreateForm(forms.ModelForm):
    class Meta:
        model = DataFormat
        exclude = ('df_type','_range_hash','range_data')

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

        self.fields['html_field_type'].label = 'Display format'

        # Generate choices for the data format
        self.fields['dfid'].choices=((dfid.pk,dfid.choice()) for dfid in DataFormat.objects.all().order_by('pk'))

        # Deal with form layout
        self.helper = QuestionEditHelper()
        self.helper.form_action = 'question_create'

class QuestionUpdateForm(QuestionCreateForm):
    def __init__(self,*args,**kwargs):
        # Note that QuestionCreateForm is called first 

        super(QuestionUpdateForm,self).__init__(*args,**kwargs)

        # Because the data_format from which we get the current choice is a separate model, we have to override the default behavior and set the initial value to the current value so that this is what shows up.
        self.fields['dfid'].initial = (self.instance.data_format.pk,self.instance.data_format.choice())

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

        # Grab data_format_id, if 'null' need to set field_params['required'] to False
        df = DataFormat.objects.get(id=self.instance.data_format_id)

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

            # catch the null questions that are there to write so jsPsych data can be added to response
            if df.df_type == 'null':
                field_params['required'] = False
                field_params['choices'] = ['null']

        elif re.match('numeric',html_field_type):
            widget = forms.NumberInput

        elif html_field_type == 'text':
            widget = forms.TextInput(attrs={'autocomplete':'off'})

        elif html_field_type == 'textarea':
            widget = forms.Textarea(attrs={'autocomplete':'off'})

        elif html_field_type == 'slider':
            widget = RangeInput(attrs=df.range_data)

            if not df.range_data:
                widget.value = 0
            else:
                widget.value = df.range_data['min']

        field_params['widget'] = widget

        if html_field_type in ['radiogroup','menu']:
            self.fields['option'] = forms.ChoiceField(**field_params)
        elif html_field_type == 'checkbox':
            self.fields['option'] = forms.MultipleChoiceField(**field_params)
        elif html_field_type == 'numeric':
            self.fields['option'] = forms.IntegerField(**field_params)
        elif html_field_type == 'slider':
            self.fields['option'] = forms.FloatField(**field_params)
        else:
            self.fields['option'] = forms.CharField(**field_params)

QuestionModelFormSet = forms.modelformset_factory(Question, form=QuestionPresentForm, extra=0, max_num=1)

class QuestionModelFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super(QuestionModelFormSetHelper, self).__init__(*args, **kwargs)
        self.template = 'pyensemble/partly_crispy/question_formset.html'
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

        widgets = {
            'form_handler': forms.Select(attrs={'placeholder':'Choose a form handler'}),
        }

    field_order = (
        'form_handler',
        'goto',
        'repeat',
        'break_loop_button',
        'break_loop_button_text',
        'continue_button_text',
        'condition_script',
        'stimulus_script',
        'record_response_script'
        )

    def __init__(self, *args, **kwargs):
        super(ExperimentFormForm,self).__init__(*args, **kwargs)

        for field in ['condition_script', 'stimulus_script', 'record_response_script']:
            script = getattr(self.instance,field,'')
            if script:
                self.fields[field].widget.attrs.update({
                    'class':'has-popover',
                    'data-content':script,
                    'data-placement':'right',
                    'data-container':'body'
                    })

class ExperimentForm(forms.ModelForm):
    class Meta:
        model=Experiment
        exclude = ('language','play_question_audio','locked','forms')

    def __init__(self, *args, **kwargs):
        super(ExperimentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.template = 'pyensemble/partly_crispy/experimentform_formset.html'
        self.helper.formset_tag = True
        self.helper.formset_method = 'POST'
        self.fields['params'].widget = forms.Textarea(attrs={'rows': 1})

ExperimentFormFormset = forms.inlineformset_factory(Experiment, ExperimentXForm, 
    form=ExperimentFormForm, 
    fields= (
        'form_order',
        'form_handler',
        'goto',
        'repeat',
        'condition_script',
        'stimulus_script',
        'break_loop_button',
        'break_loop_button_text',
        'continue_button_text',
        'use_clientside_validation',
        'record_response_script'
        ),
    can_order=True,
    can_delete=True,
    extra=0,
    )

class CopyExperimentForm(forms.ModelForm):
    class Meta:
        model=Experiment
        fields = ('title',)

        widgets = {
            'title': forms.TextInput(attrs={'placeholder':'Title of new experiment'})
        }

    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_id = 'copyItemForm'

# TODO: Refactor TicketCreationForm into a ModelForm and also make use of validfrom field
class TicketCreationForm(forms.Form):
    input_format = '%d/%m/%Y %H:%M'
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
            'dob': forms.DateInput(format='%m/%d/%Y', attrs={'placeholder':'MM/DD/YYYY'}),
        }


class RegisterSubjectUsingEmailForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = Subject
        fields = ['email', 'passphrase']


class SubjectEmailForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ('email',)
        field_classes = {
            'email': forms.EmailField,
        },
        labels = {
            'email': 'E-mail address',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'participant@example.com'})
        }

    def __init__(self, *args, **kwargs):
        super(SubjectEmailForm, self).__init__(*args, **kwargs)

        self.fields['email'].required = False

        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class LoginSubjectUsingEmailForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = Subject
        fields = ['email', 'passphrase']

    def __init__(self, *args, **kwargs):
        super(LoginSubjectUsingEmailForm, self).__init__(*args, **kwargs)

        self.fields['email'].required = True
        self.fields['passphrase'].required = True

        # Have the passphrase field be a password field
        self.fields['passphrase'].widget = forms.PasswordInput()

        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))


class CaptchaForm(forms.Form):
    captcha = ReCaptchaField()


class StudySelectForm(forms.Form):
    study = forms.ModelChoiceField(queryset=Study.objects.all())

    helper = FormHelper()
    helper.form_class = 'reporting-selector-form'
    helper.add_input(Submit('submit', 'Submit'))


class ExperimentSelectForm(forms.Form):
    experiment = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        excludes = kwargs.pop('exclude', None)
        filters = kwargs.pop('filter', None)

        super(ExperimentSelectForm, self).__init__(*args, **kwargs)

        # Get all experiment objects
        queryset=Experiment.objects.all()

        # Filter if we got filtering values
        if excludes:
            queryset = queryset.exclude(**excludes)

        if filters:
            queryset = queryset.filter(**filters)

        # Create our field
        self.fields['experiment'].queryset = queryset

    helper = FormHelper()
    helper.form_class = 'reporting-selector-form'
    helper.add_input(Submit('submit', 'Submit'))


class ExperimentResponsesForm(forms.Form):
    experiment = forms.IntegerField(widget=forms.HiddenInput())
    question = forms.MultipleChoiceField(choices=[])
    filter_excluded = forms.BooleanField(required=False, label='Remove sessions marked as excluded')
    filter_unfinished = forms.BooleanField(required=False, label='Remove incomplete sessions')

    def __init__(self, *args, **kwargs):
        super(ExperimentResponsesForm, self).__init__(*args, **kwargs)

        # Extract our experiment ID
        if 'initial' in kwargs.keys():
            experiment_id = kwargs['initial']['experiment']
        elif args:
            experiment_id = args[0]['experiment']


        # Since we are focused on ultimately gettings responses, make queries against the Response table
        experiment_responses = Response.objects.filter(experiment=experiment_id)

        # Get our list of questions that were asked in this experiment
        self.fields['question'].choices = experiment_responses.values_list('question', 'question__text').distinct()


        self.helper = FormHelper()
        self.helper.form_action = reverse('experiment-responses')
        self.helper.form_class = 'reporting-selector-form'
        self.helper.add_input(Submit('submit', 'Submit'))


class SessionFileAttachForm(forms.ModelForm):
    class Meta:
        model = SessionFile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SessionFileAttachForm, self).__init__(*args, **kwargs)
        self.fields['session'].widget = forms.HiddenInput()
