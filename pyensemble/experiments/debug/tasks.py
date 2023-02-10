# tasks.py

import datetime


from django.utils import timezone
from django.http import HttpResponse

from pyensemble.utils import defaults

from pyensemble.models import DataFormat, Question, Form, FormXQuestion, Experiment, ExperimentXForm, Notification

import pdb

def create_experiment(request):

    # Create the experiment object
    eo, created = Experiment.objects.get_or_create(
        title = 'Debug Further Participation',
        post_session_callback = 'debug.tasks.post_session()'
        )

    # Create basic data format entries
    defaults.create_default_dataformat_entries()

    dfo = DataFormat.objects.get(df_type='enum', enum_values='"Yes","No"')

    # Define some question data as a list of dictionaries
    question_data = [
        {
            'text': 'I would like to be prompted with another participation opportunity.',
            'data_format': dfo,
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
            'name': 'Desire Further Participation',
            'questions': [qo],
            'form_handler': 'form_generic'
        },
        {
            'name': 'Participant Email',
            'questions': [],
            'form_handler': 'form_subject_email'
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
        condition_script = ''

        if f['name'] == 'Participant Email':
            condition_script = 'debug.conditions.desire_further_participation()'

        efo, created = ExperimentXForm.objects.get_or_create(
            experiment = eo,
            form = fo,
            form_order = fidx,
            form_handler = f['form_handler'],
            goto = goto, # want to make this more dynamic if we add more forms to this example
            repeat = repeat,
            condition_script = condition_script
        )

    return HttpResponse('create_experiment: success')

def post_session(session, *args, **kwargs):

    # Deal with scheduling notifications
    scheduled = schedule_notifications(session, *args, **kwargs)

    return True

def schedule_notifications(session, *args, **kwargs):
    # Schedule our times. Note that these will be stored in 'UTC' and the notification will be sent at the scheduled time. So, calculate things in relation to the local time that this was completed in. These will then automatically be converted to UTC for storage in the database. Regardless of which timezone the server is running in, these will be dispatched in correctly for the user's timezone
    notification_list = []

    # pdb.set_trace()
    now = timezone.localtime()

    # Create one notification to be sent in the next dispatch cycle
    notification_list.append({
        'template': 'debug/thank_you.html',
        'context': {
            'msg_subject': 'Thank you for participating!'
        },
        'datetime': now,
    })

    # Create a notification to be sent tomorrow morning at 8:30 AM (localtime)
    tomorrow = now.date()+timezone.timedelta(days=1)
    time = datetime.time(8,30)
    target_time = timezone.datetime.combine(tomorrow, time, tzinfo=now.tzinfo)

    notification_list.append({
        'template': 'debug/reminder.html',
        'context': {
            'msg_subject': "Reminder about today's experiment",
        },
        'datetime': target_time,    
    })

    for n in notification_list:
        # Create an entry in our notifications table
        nobj = Notification.objects.create(
            subject = session.subject,
            experiment = session.experiment,
            session = session,

            template = n['template'],
            context = n['context'],
            scheduled = n['datetime'],
        )

    return True