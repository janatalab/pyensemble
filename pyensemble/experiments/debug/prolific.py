# prolific.py
#
# Testing of PyEnsemble interactions with Prolific

import datetime
import zoneinfo
import json

from django.conf import settings

from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse

from django.template import loader
from django.shortcuts import render

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


from pyensemble.models import DataFormat, Question, Form, FormXQuestion, Experiment, ExperimentXForm, Study, Session

from pyensemble.study import create_experiment_groupings

from pyensemble.integrations.prolific.prolific import Prolific
import pyensemble.integrations.prolific.utils as prolific_utils

from pyensemble.utils import qc

import pyensemble.tasks as pyensemble_tasks

import pdb

date_format_str = '%A, %B %-d'


def home(request):
    return render(request, 'debug/prolific/home.html', {})

# Create a wrapper for the integration example
def create_multiday_example(request):
    response = create_prolific_pyensemble_integration_example()

    return HttpResponse(response)


def get_prolific_pyensemble_integration_example_params():
    params = {
        'prolific_project_title': "PyEnsemble Integration Testing",
        'pyensemble_study_title': 'Prolific Multi-Day Study',
        'experiment_titles': [
            'Prolific Multi-Day Study - Day 1',
            'Prolific Multi-Day Study - Day 2',
            'Prolific Multi-Day Study - Day 3'
        ],
    }

    return params


# Create the Prolific integration example
def create_prolific_pyensemble_integration_example():
    # Fetch our general parameters
    params = get_prolific_pyensemble_integration_example_params()

    # Get our Prolific project title
    prolific_project_title = params['prolific_project_title']

    # Get our PyEnsemble study title
    pyensemble_study_title = params['pyensemble_study_title']


    """
    Deal with the PyEnsemble side of the Prolific integration.
    """

    msg = f"\nHandling the PyEnsemble side of the integration"
    print(msg)

    # Get our experiment titles
    experiment_titles = params['experiment_titles']
    
    # Create our study and experiment objects
    create_experiment_groupings({
        pyensemble_study_title: experiment_titles
    })

    # Get the study object
    study = Study.objects.get(title=pyensemble_study_title)

    # Add necessary Prolific information to the study parameters
    study.params = {
        'prolific': {
            'project_title': prolific_project_title,
            'study_collection_name': pyensemble_study_title,
        }
    }

    # Save the updated study object
    study.save()

    # Define our basic yes/no data format
    yes_no_dfo, _ = DataFormat.objects.get_or_create(
        df_type = 'enum',
        enum_values = '"Yes","No"'
        )
    
    # Define our Agree/Disagree data format (for the consent form)
    consent_dfo, _ = DataFormat.objects.get_or_create(
        df_type = 'enum',
        enum_values = '"Agree","Disagree"'
        )
 
    # Define our question data
    question_data = [
        {
            'text': 'I consent to participate in this study.',
            'data_format': consent_dfo,
            'html_field_type': 'radiogroup'
        },
        {
            'text': 'I have sufficient time to participate in this study today.',
            'data_format': yes_no_dfo,
            'html_field_type': 'radiogroup'
        },
        {
            'text': 'I would like to participate on Day 2.',
            'data_format': yes_no_dfo,
            'html_field_type': 'radiogroup'
        },
        {
            'text': 'I would like to participate on Day 3.',
            'data_format': yes_no_dfo,
            'html_field_type': 'radiogroup'
        },
    ]

    # Create our questions
    question_instances = Question.objects.none()

    for q in question_data:
        # Get or create the question
        qo, _ = Question.objects.get_or_create(**q)

        # Add the question to our question_instances QuerySet
        question_instances = question_instances | Question.objects.filter(id=qo.id)

    # Define our forms
    form_data = [
        {
            'name': 'Study Consent',
            'header': 'Consent to Participate in Research',
            'questions': question_instances.filter(text='I consent to participate in this study.'),
            'form_handler': 'form_consent'
        },
        {
            'name': 'Start Session - Day 1',
            'header': 'Welcome to the Prolific Multi-Day Study Test<br>This is Day 1',
            'questions': [],
            'form_handler': 'form_generic'
        },
        {
            'name': 'Start Session - Day 2',
            'header': 'Welcome to the Prolific Multi-Day Study Test<br>This is Day 2',
            'questions': [],
            'form_handler': 'form_generic'
        },
        {
            'name': 'Start Session - Day 3',
            'header': 'Welcome to the Prolific Multi-Day Study Test<br>This is Day 3',
            'questions': [],
            'form_handler': 'form_generic'
        },
        {
            'name': 'Enough Time',
            'questions': question_instances.filter(text='I have sufficient time to participate in this study today.'),
            'form_handler': 'form_generic'
        },
        {
            'name': 'Return Later',
            'header': 'Please return to participate in the study when you have enough time.',
            'questions': [],
            'form_handler': 'form_end_session'
        },
        {
            'name': 'Participate on Day 2',
            'questions': question_instances.filter(text='I would like to participate on Day 2.'),
            'form_handler': 'form_generic'
        },
        {
            'name': 'Participate on Day 3',
            'questions': question_instances.filter(text='I would like to participate on Day 3.'),
            'form_handler': 'form_generic'
        },
        {
            'name': 'End Session',
            'header': 'Thank you for your participation',
            'questions': [],
            'form_handler': 'form_end_session'
        }
    ]

    # Create our forms
    form_instances = Form.objects.none()

    for f in form_data:
        # Get or create the form
        fo, _ = Form.objects.get_or_create(name=f['name'])

        # Update the header 
        if 'header' in f:
            fo.header = f['header']
            fo.save()

        # Delete any existing FormXQuestion entries for this form
        FormXQuestion.objects.filter(form=fo).delete()

        # Add the questions to the form
        for idx, q in enumerate(f['questions'], start=1):
            fqo, _ = FormXQuestion.objects.get_or_create(form=fo, question=q, form_question_num=idx)

        # Add the form to our form_instances QuerySet
        form_instances = form_instances | Form.objects.filter(id=fo.id)

    # Create the ExperimentXForm entries for each experiment
    for exp_idx, experiment in enumerate(experiment_titles, start=1):
        # Get the experiment object
        experiment = Experiment.objects.get(title=experiment)

        #
        # Set additional experiment parameters
        #

        # Add a description to the experiment
        experiment.description = f"This is a test of a multi-day study run via Prolific. This is Day {exp_idx}."

        # Set our postsession callback
        experiment.post_session_callback = "debug.prolific.postsession(create_notifications=True)"

        # Set expectation of a user ticket if this is Day 2 or 3 experiment
        if exp_idx in [2, 3]:
            experiment.user_ticket_expected = True

        # Save the experiment, even if nothing changed
        experiment.save()

        # Delete any existing ExperimentXForm entries for this experiment
        ExperimentXForm.objects.filter(experiment=experiment).delete()

        # Get the form objects
        form_list = []
        if exp_idx in [1, 2]:
            if exp_idx == 1:
                form_list = ['Study Consent']

            form_list += [f'Start Session - Day {exp_idx}', 'Enough Time', 'Return Later', f'Participate on Day {exp_idx+1}', 'End Session']

        else:
            form_list = [f'Start Session - Day {exp_idx}', 'Enough Time', 'Return Later', 'End Session']


        # Create the ExperimentXForm entries
        for exf_idx, form_name in enumerate(form_list, start=1):
            # Get the form object
            form = form_instances.get(name=form_name)

            # Get the form handler from our form_data
            form_handler = next((f['form_handler'] for f in form_data if f['name'] == form_name), None)

            # Create the ExperimentXForm entry
            exf, _ = ExperimentXForm.objects.get_or_create(
                experiment = experiment,
                form = form,
                form_order = exf_idx,
                form_handler = form_handler
                )
            
            # Check whether the previous form was the "Enough Time" form
            if exf_idx > 1 and form_list[exf_idx-2] == 'Enough Time':
                # Add a callback to add to the condition script field
                exf.condition_script = "debug.prolific.not_enough_time()"

                # Save the changes
                exf.save()

            # Attach a callback in the stimulus_script field for the 'End Session' form
            if form_handler == 'form_end_session':
                exf.stimulus_script = "debug.prolific.complete_prolific_session()"

                # Save the changes
                exf.save()
            
    """
    Deal with the Prolific side of the Prolific integration.
    Note that what we refer to as an "experiment" in PyEnsemble is referred to as a "study" in Prolific.
    What we refer to as a "study" in PyEnsemble is referred to as a "study collection" in Prolific.

    The Prolific API: https://docs.prolific.com/docs/api-docs/public/
    """
    msg = f"\nHandling the Prolific side of the integration"
    print(msg)

    # Get our PyEnsemble experiments
    pyensemble_experiments = study.experiments.order_by('studyxexperiment__experiment_order')

    # Get ourselves a Prolific API object
    prolific = Prolific()

    # Create a project
    project, _ = prolific.get_or_create_project(prolific_project_title)

    # Intialize our list of Prolific study IDs
    prolific_study_ids = []

    # Create each Profilic study, i.e. corresponding to each PyEnsemble experiment
    next_participant_groups = []
    for exp_idx, experiment in enumerate(pyensemble_experiments):
        # Get our ticket for the experiment because this is how we get the external URL
        ticket = prolific_utils.get_prolific_ticket(experiment, ticket_attribute_name='Prolific Test')

        # Get or create the participant group for the next experiment
        next_experiment = experiment.studyxexperiment_set.first().next_experiment()

        if next_experiment:
            # Create the participant group if necessary
            participant_group, _ = prolific.get_or_create_group(next_experiment.title)

            # Add the participant group to our list
            next_participant_groups.append(participant_group)
        else:
            next_participant_groups.append(None)        

        # Get the default study parameters
        prolific_study_params = prolific_utils.get_default_prolific_study_params()

        # NOTE: We loaded our set of completion codes in the get_default_prolific_study_params function
        # Adding a participant to the participant group for the next study happens in the notification callback

        # Update the study parameters with the experiment title
        prolific_study_params.update({
            'name': experiment.title,
            'internal_name': experiment.title,
            'description': experiment.description,
        })

        # Update the study parameters with the external URL
        prolific_study_params.update({
            'external_study_url': prolific_utils.get_external_study_url(ticket),
        })

        # Create the study
        prolific_study, _ = prolific.get_or_create_study(prolific_study_params, project_id=project['id'])

        # Append the study ID to our list
        if prolific_study:
            prolific_study_ids.append(prolific_study['id'])

        # See if there was a preceding experiment in the sequence
        if experiment.studyxexperiment_set.first().prev_experiment():
            # Get the participant group for this experiment
            participant_group = next_participant_groups[exp_idx-1]

            # Add the participant group to this study filter
            prolific_study = prolific.add_participant_group_to_study(prolific_study['id'], participant_group['id'])

        # If this is the first experiment and we have test participants, add them to the custom_allowlist filter
        if exp_idx == 0 and settings.PROLIFIC_TESTER_IDS:
            prolific_study = prolific.add_testers_to_study(prolific_study['id'], settings.PROLIFIC_TESTER_IDS)


    msg = f"Prolific integration example created successfully. <p> The PyEnsemble study is titled {pyensemble_study_title}. <p> The Prolific project is titled {prolific_project_title}. "
    msg += f"The Prolific studies are titled: <br>"
    for experiment in pyensemble_experiments:
        msg += f"{experiment.title}<br>"

    # Generate our response message
    template_name = 'pyensemble/message.html'

    # Load the template
    template = loader.get_template(template_name)
    
    # Create the context for the template
    context = {
        'msg': msg,
        'back_url': reverse('experiments:debug:prolific-home'),
    }

    # Render the response
    response = template.render(context)
    
    return response


def test_multiday_example(request):
    # Get our parameters
    params = get_prolific_pyensemble_integration_example_params()

    project_title = params['prolific_project_title']

    msg = f"<p>Testing the studies in the Prolific project titled {project_title}.</p>"

    # Get ourselves a Prolific object
    prolific = Prolific()

    # Get the Prolific project
    project = prolific.get_project(project_title)

    # Get the studies in the Prolific project
    studies = prolific.get_project_studies(project['id'])

    # Loop over the studies and test each one
    for study in studies:
        # Test the study
        response = prolific.test_study(study['id'])

        msg += f"Transitioned the Prolific study ({response['study_id']} )to TEST mode.<br>"

    # Generate our response message
    context = {
        'msg': msg,
        'back_url': reverse('experiments:debug:prolific-home'),
    }

    return render(request, 'pyensemble/message.html', context)


# Publish the Prolific integration example
def publish_multiday_example(request):
    # Get our parameters
    params = get_prolific_pyensemble_integration_example_params()

    project_title = params['prolific_project_title']

    msg = f"<p>Publishing the studies in the Prolific project titled {project_title}.</p>"


    # Get ourselves a Prolific object
    prolific = Prolific()

    # Get the Prolific project
    project = prolific.get_project(project_title)

    # Get the studies in the Prolific project
    studies = prolific.get_project_studies(project['id'])

    # Loop over the studies and publish each one
    for study in studies:
        # Publish the study
        status = prolific.publish_study(study['id'])

        if not status:
            msg += f"FAILED to publish the Prolific study titled {study['name']}.<br>"

        else:
            msg += f"Published the Prolific study titled {study['name']}.<br>"

    # Generate our response message
    context = {
        'msg': msg,
        'back_url': reverse('experiments:debug:prolific-home'),
    }

    return render(request, 'pyensemble/message.html', context)


# Create a callback that will be used to determine whether the participant has enough time to participate in the study
def not_enough_time(request, *args, **kwargs):
    # Get our session
    session = Session.objects.get(pk=kwargs['session_id'])

    # Filter the response set to get the response to the "I have sufficient time to participate in this study today." question
    question_text = "I have sufficient time to participate in this study today."
    response = session.response_set.filter(question__text=question_text).first().response_value()

    insufficient_time = response == 'No'
    
    if insufficient_time:
        # Since we are going to exit the session, mark the ticket as unused so that the participant can 
        # participate in the study at another time
        session.ticket.used = False
        session.ticket.save()

    return insufficient_time


def qc_check(session, *args, **kwargs):
    # For now, we will just run the default quality control check (defined in pyensemble.integrity)
    # which simply checks to see if the last form of the experiment
    # has a response, but we want to add more sophisticated checks.
    passed_qc = qc.default_session_qc_check(session, *args, **kwargs)

    return passed_qc


def complete_prolific_session(request, *args, **kwargs):
    # If there is no quality control check specficied in the kwargs, 
    # we can either inject one here or let complete_prolific_session use the default one.
    if 'qc_callback' not in kwargs:
        kwargs['qc_callback'] = 'debug.prolific.qc_check()'

    return prolific_utils.complete_prolific_session(request, *args, **kwargs)


# Create a single postsession callback that can be used for all days and that runs after each day's session is completed.
# This callback needs to add the participant to the eligibility list for the next study in the sequence.
# It also needs to generate notifications for the next study in the sequence.
def postsession(session, *args, **kwargs):
    success = True

    # Get our Prolific object
    prolific = Prolific()

    # Clear any remaining unsent notifications
    pyensemble_tasks.clear_unsent_notifications(session)

    # Run any quality control checks
    passed_qc = qc.default_session_qc_check(session, *args, **kwargs)

    if not passed_qc:
        success = False
        return 

    if kwargs.get('remove_from_participant_group', False):
        # Get the Prolific submission
        submission = prolific.get_submission_by_id(session.origin_sessid)

        # Get the study ID from the submission
        study_id = submission['study_id']

        # Remove the participant from the participant group associated with this study
        groups = prolific.get_study_participant_groups(study_id)

        for group in groups:
            prolific.remove_participant_from_group(group, session.subject.subject_id)

    #
    # Determine the next experiment in the sequence
    #
    next_experiment = session.experiment.studyxexperiment_set.first().next_experiment()
    next_experiment_ticket = None

    if next_experiment:
        #
        # Create a user ticket for the next experiment
        #

        # Determine the valid ticket times
        tomorrow = session.effective_session_date()+timezone.timedelta(days=1)
        day_after_tomorrow = tomorrow+timezone.timedelta(days=1)
        
        earliest_start_time = datetime.time(5,30)
        latest_start_time = datetime.time(2,0) # late-night session, after midnight, but before 2 AM

        validfrom_datetime = timezone.datetime.combine(tomorrow, earliest_start_time, tzinfo=zoneinfo.ZoneInfo(session.timezone))
        expiration_datetime = timezone.datetime.combine(day_after_tomorrow, latest_start_time, tzinfo=zoneinfo.ZoneInfo(session.timezone))
        
        ticket_validity = {
            'user_validfrom': validfrom_datetime,
            'user_expiration': expiration_datetime
        }

        next_experiment_ticket = pyensemble_tasks.get_or_create_next_experiment_ticket(session, **ticket_validity)

    #
    # Generate our notifications
    #
    if kwargs.get('create_notifications', True):
        notifications = create_notifications(session, next_experiment_ticket=next_experiment_ticket)

    # Perform any additional actions if this is the last experiment in the sequence
    if not next_experiment:
        # If this is the last experiment in the sequence and it was successfully approved, approve the submissions
        # for the preceding experiments as approved also.
        if passed_qc:
            success = prolific_utils.approve_previous_submissions(session)

    return success

def create_notifications(session, next_experiment_ticket=None):
    # Create a list of dictionaries with notification parameters
    notification_list = []

    # Get the current study name
    is_prolific = session.subject.id_origin == 'PRLFC'

    # Default the current study name to the session's experiment title
    current_study_name = ""

    if is_prolific:
        # Get a Prolific object
        prolific = Prolific()

        # Get the Prolific study by its internal name
        study = prolific.get_study_by_internal_name(session.experiment.title)

        # Get the Prolific study name
        if study:
            current_study_name = study['name']
        
    if not current_study_name:
        # Get the current study name from the session's experiment
        current_study_name = session.experiment.title

    # Get the next experiment in the sequence
    next_experiment = session.experiment.studyxexperiment_set.first().next_experiment()

    next_study_name = ""
    if next_experiment:
        if is_prolific:
            # Get the Prolific study for the next experiment
            next_experiment_study = prolific.get_study_by_internal_name(next_experiment.title)

            # Get the Prolific study name
            if next_experiment_study:
                next_study_name = next_experiment_study['name']
        
        if not next_study_name:
            next_study_name = next_experiment.title

        next_experiment_params = json.loads(next_experiment.params)

    else:
        next_experiment_params = {}
        

    # Specify the template for all of this day's notifications
    notification_template = f'debug/notifications/prolific_multiday.html'

    # Create a thank you notification, that contains a reminder about the next experiment day
    # Create one notification to be sent in the next dispatch cycle
    curr_experiment_order = session.experiment.studyxexperiment_set.first().experiment_order
    notification_list.append({
        'session': session,
        'ticket': next_experiment_ticket,
        'template': notification_template,
        'context': {
            'msg_number': len(notification_list)+1,
            'msg_subject': f'Thank you for participating in the study titled {current_study_name}!',
            'study_name': current_study_name,
            'next_study_name': next_study_name,
            'curr_experiment_order': curr_experiment_order,
        },
        'datetime': session.end,
        'callback_for_dispatch': 'debug.prolific.thank_you_notification()',
    })

    # Create additional notifications for the next experiment day

    if next_experiment:
        # Get the experiment order in the study of this experiment
        next_experiment_order = next_experiment.studyxexperiment_set.first().experiment_order

        # Create a notification to be sent at the time at which  the ticket for the next experiment 
        # becomes valid. It is at this time that the participant will be added to the participant
        # group for the next experiment.
        
        # Get our session's timezone info
        # NOTE: Can this be moved to the Session model?
        session_tz = session.timezone
        if not session_tz:
            session_tz = 'UTC'

        session_tzinfo = zoneinfo.ZoneInfo(session_tz)

        # target_time = timezone.datetime.combine(tomorrow, earliest_start_time, tzinfo=session_tzinfo)
        target_time = next_experiment_ticket.start
        target_date = target_time.date()

        notification_list.append({
            'session': session,
            'ticket': next_experiment_ticket,
            'template': notification_template,
            'context': {
                'msg_number': len(notification_list)+1,
                'msg_subject': f"Day {next_experiment_order} Study Reminder",
                'study_name': current_study_name,
                'next_study_name': next_study_name,
                'curr_experiment_order': curr_experiment_order,
                'prolific_study_name': next_study_name,
                'study_duration': next_experiment_params.get('total_experiment_duration_m', None),
            },
            'datetime': target_time,
            'callback_for_dispatch': 'debug.prolific.experiment_available_notification()',
        })

        # Create a reminder notification to be sent at 6 PM (localtime) on the next experiment day.
        time = datetime.time(18,00)
        target_time = timezone.datetime.combine(target_date, time, tzinfo=session_tzinfo)

        # Generate the notification
        notification_list.append({
            'session': session,
            'ticket': next_experiment_ticket,
            'template': notification_template,
            'context': {
                'msg_number': len(notification_list)+1,
                'msg_subject': f"Day {next_experiment_order} FINAL PARTICIPATION REMINDER ",
                'next_study_name': next_study_name,
                'prolific_study_name': next_study_name,
                'study_duration': next_experiment_params.get('total_experiment_duration_m', None),
            },
            'datetime': target_time,
            'callback_for_dispatch': 'debug.prolific.experiment_expiring_notification()',
        })

    # Generate the notifications
    notifications = pyensemble_tasks.create_notifications(session, notification_list)

    return notifications

# Create a form to register a Prolific test subject
class ProlificTestSubjectForm(forms.Form):
    # Define the form fields
    prolific_id = forms.CharField(label='Prolific ID', max_length=100)

    helper = FormHelper()
    # Limit widget width to 50% of the page
    # helper.form_class = 'form-inline'
    # helper.label_class = 'col-sm-2'
    # helper.field_class = 'col-lg-6'
    helper.add_input(Submit('submit', 'Submit'))
    

class ProlificTesterEmailForm(forms.Form):
    # Define a field for the email address
    email = forms.EmailField(label='Prolific Tester Account Email', max_length=100)

    def __init__(self, *args, **kwargs):
        super(ProlificTesterEmailForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))

def tester_fetch(request):
    # Fetch the Prolific participant ID for a test account
    if request.method == 'POST':
        # Get the Prolific ID from the form
        form = ProlificTesterEmailForm(request.POST)

        if form.is_valid():
            # Get the Prolific ID from the form
            email = form.cleaned_data['email']

            # Get the Prolific API object
            prolific = Prolific()

            # Construct the Prolific API endpoint
            endpoint = prolific.api_endpoint + "researchers/participants/"

            # Post the test participant email
            response = prolific.session.post(endpoint, json={"email": email})

            # Check the response status code
            context = {}
            if response.status_code == 201:
                context.update({'participant_id': response.json()['participant_id']})
            
            else:
                # Handle the error
                context.update({'error': response.json()['error']})

            # Render the response through the PyEnsemble message interface
            if 'error' in context:
                context.update({'msg': f"Error: {context['error']}"})
            else:
                context.update({'msg': f"Prolific ID: {context['participant_id']}"})

            context.update({'back_url': reverse('experiments:debug:prolific-home')})
            return render(request, 'pyensemble/message.html', context)
    else:
        # Render the form to register a Prolific test subject
        form = ProlificTesterEmailForm()

    return render(request, 'debug/prolific/register_test_subject.html', {'form': form})

# Create a view to register a Prolific text subject
def register_test_subject(request):
    # Get the Prolific ID from the POST request
    # Use the Django flow to get the Prolific ID from the request
    # Note that this is a POST request, so we need to use request.POST
    if request.method == 'POST':
        # Validate the form
        form = ProlificTestSubjectForm(request.POST)

        if form.is_valid():
            # Get the integration example params
            params = get_prolific_pyensemble_integration_example_params()

            # Get the Prolific API object
            prolific = Prolific()

            # Get the PyEnsemble study
            study = Study.objects.get(title=params['pyensemble_study_title'])

            # Get the first experiment in the study
            experiment = study.experiments.order_by('studyxexperiment__experiment_order').first()

            # Get the Prolific project
            project = prolific.get_project(params['prolific_project_title'])

            if not project:
                msg = f"Prolific project {params['prolific_project_title']} does not exist. Please create the project in Prolific."
                return render(request, 'pyensemble/message.html', {'msg': msg})
            
            # Get the Prolific study 
            study = prolific.get_study_by_name(experiment.title, project_id=project['id'])

            if not study:
                msg = f"Prolific study {experiment.title} does not exist. Please create the study in Prolific."
                return render(request, 'pyensemble/message.html', {'msg': msg})

            # Get the Prolific ID from the form
            prolific_id = form.cleaned_data['prolific_id']

            # By default the subject is not yet registered
            subject_registered = False

            # Get the current set of filters
            filters = study['filters']

            custom_allowlist_filter = None

            # Find the 'custom_allowlist' filter in the filters list
            for f in filters:
                if f['filter_id'] == 'custom_allowlist':
                    custom_allowlist_filter = f

                    # Check if the Prolific ID is already in the allow list
                    if prolific_id in f['selected_values']:
                        subject_registered = True
                        msg = f"Prolific ID {prolific_id} is already registered for the study titled, {study['name']}."
                        break

            # If the subject is not registered, add them to the allow list
            if not subject_registered:
                # If the 'custom_allowlist' filter is not found, create it
                if not custom_allowlist_filter:
                    # Create the filter
                    custom_allowlist_filter = {
                        'filter_id': 'custom_allowlist',
                        'selected_values': [],
                    }

                    # Add the filter to the filters list
                    filters.append(custom_allowlist_filter)

                # Add the participant to the filter
                custom_allowlist_filter['selected_values'].append(prolific_id)

                # Update the study with the new filter
                study = prolific.update_study(study, filters=filters)

                context = {
                    'msg': f"Prolific ID {prolific_id} has been added to the allow list for the study titled, {study['name']}.",
                    'back_url': reverse('experiments:debug:prolific-home'),
                }

            # Render the response through the PyEnsemble message interface
            return render(request, 'pyensemble/message.html', context)

    else:
        # Render the form to register a Prolific text subject
        form = ProlificTestSubjectForm()

    return render(request, 'debug/prolific/register_test_subject.html', {'form': form})


def delete_multiday_example(request):
    # Get our parameters
    params = get_prolific_pyensemble_integration_example_params()

    # Get ourselves a Prolific object
    prolific = Prolific()

    # Delete the Prolific project
    prolific.delete_project_studies(params['prolific_project_title'])

    # Delete the PyEnsemble study
    # Study.objects.filter(title=params['pyensemble_study_title']).delete()

    msg = "Deleted the studies in the Prolific project."

    context = {
        'msg': msg,
        'back_url': reverse('experiments:debug:prolific-home'),
    }

    return render(request, 'pyensemble/message.html', context)


def delete_pyensemble_example(request):
    # Get our parameters
    params = get_prolific_pyensemble_integration_example_params()

    # Get the study object
    study = Study.objects.get(title=params['pyensemble_study_title'])

    # Delete the experiments in the study
    '''
        Delete the experiment
        Doing this will delete the following objects:
        'pyensemble.Response'
        'pyensemble.ExperimentXForm'
        'pyensemble.ExperimentXAttribute'
        'pyensemble.StudyXExperiment'
        'pyensemble.Session'
        'pyensemble.Ticket'
        'pyensemble.Experiment'
    '''
    for experiment in study.experiments.order_by('studyxexperiment__experiment_order'):
        # We need to delete the forms associated with the experiment

        # Get the form objects
        form_instances = experiment.forms.all()
        for form in form_instances:
            # Get the form questions
            form_questions = form.questions.all()
            for fq in form_questions:
                # Delete the FormXQuestion objects
                fq.delete()
             
            # Delete the form
            form.delete()

        experiment.delete()

    # Delete the PyEnsemble study
    Study.objects.filter(title=params['pyensemble_study_title']).delete()

    context = {
        'msg': "Deleted the PyEnsemble study.",
        'back_url': reverse('experiments:debug:prolific-home'),
    }

    return render(request, 'pyensemble/message.html', context)

# 
# Define our various notification callbacks
#
def send_message(context):
    # Send the message via the Prolific API
    # Get the Prolific object
    prolific = Prolific()

    # Get our template
    template = loader.get_template(context['template'])

    # Render the message content
    body = template.render(context)

    # Get the Prolific submission
    submission = prolific.get_submission_by_id(context['session'].origin_sessid)

    # Create the Prolific payload
    json_data = {
        'recipient_id': context['session'].subject.subject_id,
        'body': body,
        'study_id': submission['study_id']
    }

    resp = prolific.send_message(json_data)

    return resp


def thank_you_notification(request, *args, **kwargs):
    # We can pass straight through to the dispatch_notification function
    resp = send_message(kwargs)

    return resp


def experiment_available_notification(request, *args, **kwargs):
    # We need to add the participant to the participant group for the next experiment

    # Get the Prolific object
    prolific = Prolific()

    # Get the ticket
    ticket = kwargs['ticket']

    # Get our Prolific group for the next experiment
    group = prolific.get_group_by_name(ticket.experiment.title)

    # Add the participant to the group
    # This may have already been achieved using the completion code
    result = prolific.add_participant_to_group(group['id'], ticket.subject.subject_id)

    # Verify that the participant was added to the group
    if not result:
        # Raise an error
        msg = f"Failed to add the participant to the group {group['name']} for the study {ticket.experiment.title}."
        raise Exception(msg)
    
    # Send the message
    resp = send_message(kwargs)

    return resp

def experiment_expiring_notification(request, *args, **kwargs):
    # We can pass straight through to the dispatch_notification function
    resp = send_message(kwargs)

    return resp
