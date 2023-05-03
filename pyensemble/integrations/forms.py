# forms.py

import django.forms as forms
from django.forms.widgets import TextInput

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class SpotifyImportForm(forms.Form):
    playlist_uri = forms.CharField(label='Specify a Spotify playlist URI')
    attributes = forms.CharField(
        label='(optional) Attributes', 
        widget=TextInput(attrs={'placeholder':'Enter one or more attribute labels (comma-separated)'}),
        required=False)

    def __init__(self, *args, **kwargs):
        super(SpotifyImportForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'importform'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', 'Submit'))
