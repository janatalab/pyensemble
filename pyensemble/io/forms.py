# eeg_groove/forms.py

import django.forms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

import pdb


class PortAddressForm(forms.Form):
    address = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
        super(PortAddressForm, self).__init__(*args, **kwargs)


class CodeForm(forms.Form):
    code = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
        super(CodeForm, self).__init__(*args, **kwargs)


class TimingTestForm(CodeForm):
    interval = forms.FloatField()

    def __init__(self, *args, **kwargs):
        super(TimingTestForm, self).__init__(*args, **kwargs)

        self.fields['interval'].label = "Interval (sec)"

        # Modify our submit button
        start_button = self.helper.inputs[0]
        start_button.name = 'start'
        start_button.value = 'Start'
        start_button.field_classes = 'btn btn-success'

        self.helper.add_input(Submit('stop', 'Stop', css_class="btn-warning"))

        self.helper.add_input(Submit('end', 'End', css_class="btn-danger"))
