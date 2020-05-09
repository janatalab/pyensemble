# forms.py
import django.forms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class ImportForm(forms.Form):
    file = forms.FileField(label='Select a .csv or .json file to import')

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'importform'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
        super(ImportForm, self).__init__(*args, **kwargs)
