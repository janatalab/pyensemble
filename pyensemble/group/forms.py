# forms.py

#
# Support for group sessions
#

import django.forms as forms
from django.core.exceptions import ValidationError

from .models import Group, GroupSession
from pyensemble.models import Ticket, Experiment

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

import pdb

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group

        exclude = ()

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))

def get_group_code_form(code_type='participant'):
    if code_type == 'participant':
        code_field = 'participant_code'
        field_label = 'Code provided by experimenter'

    elif code_type == 'experimenter':
        code_field = 'experimenter_code'
        field_label = 'Experimenter code'

    else:
        raise ValueError(f'code_type {code_type} is not a valid code type')

    class GroupCodeForm(forms.ModelForm):
        class Meta:
            model = Ticket
            fields = (code_field,)
            labels = {
                code_field: field_label,
            }

        def __init__(self, *args, **kwargs):
            super(GroupCodeForm, self).__init__(*args, **kwargs)

            self.helper = FormHelper()
            self.helper.form_method = 'post'
            self.helper.add_input(Submit('submit', 'Submit'))

        def clean_participant_code(self):
            return self.check_code()

        def clean_experimenter_code(self):
            return self.check_code()

        def check_code(self):
            data = self.cleaned_data[code_field]

            # See whether a group ticket with this participant_code exists
            try:
                ticket_info = {code_field: data, 'type': 'group'}
                ticket = Ticket.objects.get(**ticket_info)

            except:
                if Ticket.objects.filter(**ticket_info).count():
                    ticket = Ticket.objects.filter(**ticket_info).last()

                else:
                    raise ValidationError('Failed to retrieve ticket matching this code')

            # Check for ticket expiration
            if ticket.expired:
                raise ValidationError('The ticket matching this code has expired')

            return data     

    return GroupCodeForm


class GroupSessionForm(forms.ModelForm):
    class Meta:
        model = GroupSession
        fields = ('experiment', 'group')

    def __init__(self, *args, **kwargs):
        super(GroupSessionForm, self).__init__(*args, **kwargs)

        # Generate the set of possible experiment choices
        self.fields['experiment'] = forms.ModelChoiceField(queryset=Experiment.objects.filter(is_group=True), empty_label=None)

        # Generate a set of possible group choices, including a new group
        self.fields['group'] = forms.ModelChoiceField(queryset=Group.objects.all(), empty_label='New Group')
        self.fields['group'].required = False

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit'))


class GroupSessionNotesForm(forms.ModelForm):
    class Meta:
        model = GroupSession
        fields = ('notes',)

    def __init__(self, *args, **kwargs):
        super(GroupSessionNotesForm, self).__init__(*args, **kwargs)

        self.fields['id'] = forms.IntegerField(widget=forms.HiddenInput)
        self.fields['notes'] = forms.CharField(widget=forms.Textarea(attrs={'rows':5}))
        self.fields['notes'].label = ''
        self.fields['notes'].required = False

        self.helper = FormHelper()
        self.helper.form_id = 'session-notes-form'
        self.helper.form_method = 'post'


class GroupSessionFileAttachForm(form.ModelForm):
    class Meta:
        model = GroupSessionFile
        fields = '__all__'      

