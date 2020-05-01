# forms.py
import re

from django.conf import settings

import django.forms as forms
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import LayoutObject, Layout, Field, Submit, Row, Div, Fieldset
from crispy_forms.bootstrap import InlineRadios, InlineCheckboxes, UneditableField

from pyensemble.models import FormXQuestion, Question, Subject, Form, Experiment, ExperimentXForm

import pdb

# class FormModelForm(forms.ModelForm):
#     class Meta:
#         model = Form

class ImportForm(forms.Form):
    file = forms.FileField(label='Select a .csv or .json file to import')

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'importform'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
        super(ImportForm, self).__init__(*args, **kwargs)

class CreateQuestionForm(forms.ModelForm):
    helper = FormHelper()
    helper.form_method = 'POST'

    class Meta:
        model=Question
        fields=('text','category','data_format','value_range','value_default','html_field_type','locked','audio_path')

        widgets = {
            'text': forms.TextInput(attrs={'placeholder':'Enter the question text here'}),
        }

# borrowed this from meamstream
class QuestionModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuestionModelForm, self).__init__(*args, **kwargs)

        use_crispy = True
        field_params = {'required': False}

        # Set up the input field as a function of the HTML type
        # html_field_type = self.instance.questionxdataformat_set.get().html_field_type
        html_field_type = self.instance.html_field_type

        # If a field type hasn't been specified, choose radiogroup as a default
        if not html_field_type:
            html_field_type = 'radiogroup'

        if html_field_type in ['radiogroup', 'checkbox','menu']:
            # Deal with getting our choices
            # pdb.set_trace()
            # enum_value_str = self.instance.values.all().values_list('enum_values',flat=True)[0]
            # field_params['choices'] = [(val,lbl) for val,lbl in enumerate(enum_value_str.replace('"','').replace('\\','').split(','))]
            field_params['choices'] = self.instance.choices()

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
        self.fields['option'].label = self.instance.text

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

class ExperimentFormForm(forms.ModelForm):
    # form_name = forms.CharField()

    class Meta:
        model = ExperimentXForm
        exclude = ('form_order',)

    field_order = ('form_handler','goto','repeat','break_loop_button','break_loop_button_text','condition_script','stimulus_script')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.fields['form_name'].initial = self.instance.form.name

        # pdb.set_trace()
        # formtag_prefix = re.sub('-[0-9]+$', '', kwargs.get('prefix', ''))

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                UneditableField('form_order'),
                # Field('form'),
                Field('form_handler'),
                Field('goto'),
                Field('repeat'),
                Field('condition_script'),
                Field('stimulus_script'),
                Field('break_loop_button'),
                Field('break_loop_button_text'),
                Field('DELETE'),
                # css_class='formset_row-{}'.format(formtag_prefix)
            )
        )

class ExperimentForm(forms.ModelForm):
    class Meta:
        model=Experiment
        exclude = ('language','play_question_audio','params','locked','forms')

    def __init__(self, *args, **kwargs):
        super(ExperimentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.template = 'pyensemble/crispy_overrides/experiment_formset.html'
        self.helper.form_tag = True
        self.helper.formset_tag = True
        self.helper.formset_method = 'POST'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3 create-label d-none'
        # self.helper.field_class = 'col-md-9'
        self.helper.field_class = 'col'
        # self.helper.layout = Layout(
        #     Div(
        #         Field('description'),
        #         Fieldset(ExpFormFormset('formset')),
        #         # HTML("<br>"),
        #         # ButtonHolder(Submit('submit', 'Save')),
        #     )
        # )


ExperimentFormFormset = forms.inlineformset_factory(Experiment, ExperimentXForm, 
    form=ExperimentFormForm, 
    fields=('form_order', 'form_handler', 'goto','repeat','condition_script','stimulus_script', 'break_loop_button', 'break_loop_button_text'), 
    can_order=True,
    can_delete=True,
    extra=0,
    )


# class ExpFormFormset(LayoutObject):
#     template = "pyensemble/partly_crispy/expform_formset.html"

#     def __init__(self, formset_name_in_context, template=None):
#         self.formset_name_in_context = formset_name_in_context
#         self.fields = []
#         if template:
#             self.template = template
#         # pdb.set_trace()

#     def render(self, form, form_style, context, template_pack=settings.CRISPY_TEMPLATE_PACK):
#         formset = context[self.formset_name_in_context]
#         return render_to_string(self.template, {'formset': formset})

# class AddFormForm(forms.ModelForm):
#     class Meta:
#         model = Form
#         fields = ('name',)

#         widgets = {
#             'name': forms.TextInput(attrs={'disabled': True}),
#         }     

# class AddFormHelper(FormHelper):
#     def __init__(self, *args, **kwargs):
#         super(AddFormHelper, self).__init__(*args, **kwargs)
#         self.form_method = 'POST'
#         self.form_show_labels = False
#         self.layout = Layout(
#             Row(
#                 Field('add'),
#                 Field('order'),
#                 Field('name'),
#             )
#         )   

# AddFormFormset = forms.modelformset_factory(Form, form=AddFormForm)

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
