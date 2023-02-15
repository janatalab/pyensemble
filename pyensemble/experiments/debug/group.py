# group.py

from pyensemble.models import DataFormat, Question, Form, FormXQuestion, ExperimentXForm, Experiment

from django.http import HttpResponse

from pyensemble.group.views import get_group_session, init_group_trial

import pdb

def create_group_experiment(request):
    # Instantiates necessary response options, questions, forms, and experiment to test running a group experiment.

    # Create the experiment object
    eo, created = Experiment.objects.get_or_create(title='Debug Group Experiment', is_group=True)

    # Define some data formats as a list of dictionaries
    data_formats = [
        {
            'df_type': 'enum',
            'enum_values': '"Yes","No"',
        },
        {
            'df_type': 'enum',
            'enum_values': '"Strongly Disagree","Somewhat Disagree","Neither Agree nor Disagree","Somewhat Agree","Strongly Agree"',
        },
        {
            'df_type': 'int',
        }
    ]

    # Upload the data formats
    for df in data_formats:
        dfo, created = DataFormat.objects.get_or_create(**df)

        if "Disagree" in dfo.enum_values:
            disagree_dfo = dfo

    # Define some question data as a list of dictionaries
    question_data = [
        {
            'text': 'I experienced this trial to be difficult.',
            'data_format': disagree_dfo,
            'html_field_type': 'radiogroup'
        }
    ]

    for q in question_data:
        qo, created = Question.objects.get_or_create(**q)

    # Define form data, including data that we will populate ExperimentXForm with
    form_data = [
        {
            'name': 'Start Session',
            'questions': [],
            'form_handler': 'form_subject_register'
        },
        {
            'name': 'Wait',
            'questions': [],
            'header': 'Please wait for instructions from the experimenter.',
            'form_handler': 'form_generic'
        },
        {
            'name': 'Debug Group Post Trial',
            'questions': [qo],
            'form_handler': 'group_trial'
        },
        {
            'name': 'Debug Group Feedback',
            'questions': [],
            'form_handler': 'group_trial'
        },
        {
            'name': 'End Session',
            'header': 'Thank you for your participation',
            'questions': [],
            'form_handler': 'form_end_session'
        }
    ]

    # Delete any existing ExperimentXForm entries for this experiment
    ExperimentXForm.objects.filter(experiment=eo).delete()

    for fidx, f in enumerate(form_data, start=1):
        fo, created = Form.objects.get_or_create(name=f['name'])

        for idx, q in enumerate(f['questions'], start=1):
            fqo, created = FormXQuestion.objects.get_or_create(form=fo, question=q, form_question_num=idx)

        # Link the form into the experiment, implementing some looping logic along the way
        goto = None
        repeat = None
        stimulus_script = ''

        if f['name'] == 'Debug Group Post Trial':
            stimulus_script = 'debug.group.init_trial()'

        elif f['name'] == 'Debug Group Feedback':
            goto = [f['name'] for f in form_data].index('Debug Group Post Trial')+1
            repeat = 10
            stimulus_script = 'debug.group.trial_feedback()'

        efo, created = ExperimentXForm.objects.get_or_create(
            experiment=eo,
            form = fo,
            form_order = fidx,
            form_handler = f['form_handler'],
            goto = goto, # want to make this more dynamic if we add more forms to this example
            repeat = repeat,
            stimulus_script = stimulus_script
            )


    return HttpResponse('create_group_experiment: success')

# Each participant's session calls this init_trial once the serve_form method has determined that everyone in the group is ready
def init_trial(request, *args, **kwargs):
    # Initialize our trial
    trial_data = init_group_trial()

    # Get the group's session
    group_session = get_group_session(request)

    # Do whatever you want with the knowledge of which group and participants we are dealing with, e.g. checking for previous responses, etc.
    trial_data['autorun'] = True # Set to true if participants view are NOT controlled by an experimenter process that sets trial state 'ended'
    
    return trial_data

def trial_feedback(request, *args, **kwargs):
    # Initialize our trial
    trial_data = init_group_trial()

    # Get the group's session
    group_session = get_group_session(request)

    # Do whatever you want with the knowledge of which group and participants we are dealing with, e.g. checking for previous responses, etc.
    trial_data['feedback'] = f'There are {group_session.num_users} participants connected to this session'

    return trial_data