# pyensemble/widgets.py

from django.forms.widgets import NumberInput

class RangeInput(NumberInput):
    input_type = 'range'
    template_name = 'pyensemble/widgets/slider.html'