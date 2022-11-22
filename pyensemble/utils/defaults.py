# defaults.py
#
# Methods that serve in lieu of data migrations, i.e. populate specific data tables with desired default values.

from pyensemble.models import DataFormat

def create_default_dataformat_entries():
    default_df = [
        {
            'df_type': 'null',
            'enum_values': ''
        },
        {
            'df_type': 'int',
            'enum_values': ''
        },
        {
            'df_type': 'float',
            'enum_values': ''
        },
        {
            'df_type': 'char',
            'enum_values': ''
        },
        {
            'df_type': 'enum',
            'enum_values': '"Yes","No"'
        },
        {
            'df_type': 'enum',
            'enum_values': '"Strongly Disagree","Somewhat Disagree","Neither Agree nor Disagree","Somewhat Agree","Strongly Agree"'
        },
    ]

    for df in default_df:
        obj, created = DataFormat.objects.get_or_create(**df)
