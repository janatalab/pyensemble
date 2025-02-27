# prolific.py
#
# Testing of PyEnsemble interactions with Prolific

import datetime
import zoneinfo

from django.utils import timezone
from django.http import HttpResponse

from django.template import loader
from django.shortcuts import render

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


from pyensemble.models import DataFormat, Question, Form, FormXQuestion, Experiment, ExperimentXForm, Study, Notification
from pyensemble.study import create_experiment_groupings

from pyensemble.integrations.prolific.prolific import Prolific

from pyensemble.tasks import create_tickets, get_or_create_next_experiment_ticket, create_notifications

import pdb

date_format_str = '%A, %B %-d'


def get_default_prolific_study_params():
    # Create a dictionary containing the set of required params to create a Prolific study
    # The dictionary will contain the following
    # - study_name: The name of the study
    # - description: A description of the study that participants will read
    # - external_study_url: This is the PyEnsemble URL that participants will be directed to, along with the Prolific participant ID
    # - prolific_id_option: "url_parameters"
    # - reward: in cents
    # - total_available_places: The number of participants that can participate in the study
    # - estimated_completion_time: The estimated time to complete the study
    # - completion_codes: An array of completion codes that will be returned to Prolific
    default_study_params = {
        'name': "",
        'description': "",
        'external_study_url': "",
        'prolific_id_option': "url_parameters",
        'reward': 15,
        'total_available_places': 1,
        'estimated_completion_time': 1,
        'completion_codes': None,
        'device_compatibility': ["desktop"],
    }

    return default_study_params


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
    dfo, _ = DataFormat.objects.get_or_create(
        df_type = 'enum',
        enum_values = '"Yes","No"'
        )
    
    # Define our question data
    question_data = [
        {
            'text': 'I would like to be participate on Day 2.',
            'data_format': dfo,
            'html_field_type': 'radiogroup'
        },
        {
            'text': 'I would like to be participate on Day 3.',
            'data_format': dfo,
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
            'name': 'Participate on Day 2',
            'questions': question_instances.filter(text='I would like to be participate on Day 2.'),
            'form_handler': 'form_generic'
        },
        {
            'name': 'Participate on Day 3',
            'questions': question_instances.filter(text='I would like to be participate on Day 3.'),
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
        if exp_idx in [1, 2]:
            form_list = [f'Start Session - Day {exp_idx}', f'Participate on Day {exp_idx+1}', 'End Session']

        else:
            form_list = [f'Start Session - Day {exp_idx}', 'End Session']


        # Create the ExperimentXForm entries
        for exf_idx, form_name in enumerate(form_list, start=1):
            # Get the form object
            form = form_instances.get(name=form_name)

            # Get the form handler from our form_data
            form_handler = next((f['form_handler'] for f in form_data if f['name'] == form_name), None)

            # Create the ExperimentXForm entry
            ExperimentXForm.objects.get_or_create(
                experiment = experiment,
                form = form,
                form_order = exf_idx,
                form_handler = form_handler
                )
            
    """
    Deal with the Prolific side of the Prolific integration.
    Note that what we refer to as an "experiment" in PyEnsemble is referred to as a "study" in Prolific.
    What we refer to as a "study" in PyEnsemble is referred to as a "study collection" in Prolific.

    The Prolific API: https://docs.prolific.com/docs/api-docs/public/
    """
    msg = f"\nHandling the Prolific side of the integration"
    print(msg)

    # Get ourselves a Prolific API object
    prolific = Prolific()

    # Create a project
    project, _ = prolific.get_or_create_project(prolific_project_title)

    # Intialize our list of Prolific study IDs
    prolific_study_ids = []

    # Create each Profilic study, i.e. corresponding to each PyEnsemble experiment
    for experiment in study.experiments.order_by('studyxexperiment__experiment_order'):
        # Get our ticket for the experiment because this is how we get the external URL
        ticket_attribute_name = 'Prolific Test'
        tickets = experiment.ticket_set.filter(attribute__name=ticket_attribute_name)

        if not tickets.exists():
            # Create a dictionary containing the ticket request data
            ticket_request_data = {
                'experiment': experiment,
                'type': 'master',
                'attribute': ticket_attribute_name,
                'num_master': 1,
                'timezone': 'UTC'
            }

            # Create the ticket
            ticket = create_tickets(ticket_request_data).first()
        
        else:
            ticket = tickets.first()

        # Get the default study parameters
        prolific_study_params = get_default_prolific_study_params()

        # Update the study parameters with the experiment title
        prolific_study_params.update({
            'name': experiment.title,
            'description': experiment.description,
            'completion_codes': [
                {
                    "code": "ABC123",
                    "code_type": "COMPLETED",
                    "actions": [
                        {
                            "action": "AUTOMATICALLY_APPROVE"
                        }
                    ]
                }
            ]
        })

        # Update the study parameters with the external URL
        pid_str = "{{%PROLIFIC_PID%}}"
        study_id_str = "{{%STUDY_ID%}}"
        prolific_study_params.update({
            'external_study_url': f"{ticket.url}&PROLIFIC_PID={pid_str}&STUDY_ID={study_id_str}"
        })

        # Create the study
        prolific_study, _ = prolific.get_or_create_study(prolific_study_params, project_id=project['id'])

        # Append the study ID to our list
        if prolific_study:
            prolific_study_ids.append(prolific_study['id'])

        # Create a participant group for this study, if applicable
        # See if there was a preceding experiment in the sequence
        if experiment.studyxexperiment_set.first().prev_experiment():
            # Create the participant group if necessary
            participant_group, _ = prolific.get_or_create_group(experiment.title)

            # Add the participant group to this study filter
            status = prolific.add_participant_group_to_study(prolific_study, participant_group)

    msg = f"Prolific integration example created successfully. <p> The Prolific project is titled {prolific_project_title}. <p> The PyEnsemble study is titled {pyensemble_study_title}. <p> The Prolific study collection is titled {pyensemble_study_title}."
    msg += f"<p> The Prolific studies are titled:</p>"
    for experiment in study.experiments.order_by('studyxexperiment__experiment_order'):
        msg += f"{experiment.title}<br>"

    # Generate our response message
    template_name = 'pyensemble/message.html'

    # Load the template
    template = loader.get_template(template_name)
    
    # Render the response
    response = template.render({'msg': msg})
    
    return response


# Publish the Prolific integration example
def publish_multiday_example(request):
    # Get our paramters
    params = get_prolific_pyensemble_integration_example_params()

    # Get ourselves a Prolific object
    prolific = Prolific()

    # Get the Prolific project
    project = prolific.get_project(params['prolific_project_title'])

    # Get the studies in the Prolific project

    # Loop over the studies and publish each one

    return render(request, 'pyensemble/message.html', {'msg': msg})


# Create a single postsession callback that can be used for all days and that runs after each day's session is completed.
# This callback needs to add the participant to the eligibility list for the next study in the sequence.
# It also needs to generate notifications for the next study in the sequence.
def postsession(session, *args, **kwargs):
    # Run any quality control checks
    passed_qc = True

    # Add checks here

    if not passed_qc:
        # Note that quality control failed
        return {'qc_failed': True}
    
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
        tomorrow = session.effective_end_date()+timezone.timedelta(days=1)
        day_after_tomorrow = tomorrow+timezone.timedelta(days=1)
        
        earliest_start_time = datetime.time(5,30)
        latest_start_time = datetime.time(2,0) # late-night session, after midnight, but before 2 AM

        validfrom_time = timezone.datetime.combine(tomorrow, earliest_start_time, tzinfo=zoneinfo.ZoneInfo(session.timezone))
        expiration_datetime = timezone.datetime.combine(day_after_tomorrow, latest_start_time, tzinfo=zoneinfo.ZoneInfo(session.timezone))
        
        ticket_validity = {
            'user_validfrom': validfrom_time,
            'user_expiration': expiration_datetime
        }

        next_experiment_ticket = get_or_create_next_experiment_ticket(session, **ticket_validity)

        #
        # Since we are dealing with a Prolific session, 
        # we need to add this participant to the eligibility list for the next study in the sequence.
        #

        # Get ourselves a Prolific API object
        prolific = Prolific()

        # Get our Prolific group for the next experiment
        group = prolific.get_group_by_name(next_experiment_ticket.experiment.title)

        # Add the participant to the group
        result = prolific.add_participant_to_group(group['id'], session.subject.subject_id)

        # Verify that the participant was added to the group
        if not result:
            return {'prolific_group_add_failed': True}

    #
    # Generate our notifications
    #
    if kwargs.get('create_notifications', True):
        # Create a list of dictionaries with notification parameters
        notification_list = []

        # Specify the template for all of this day's notifications
        notification_template = f'debug/notifications/prolific_multiday.html'

        # Create a thank you notification, that contains a reminder about the next experiment day
        # Create one notification to be sent in the next dispatch cycle
        curr_experiment_order = session.experiment.studyxexperiment_set.first().experiment_order
        notification_list.append({
            'session': session,
            'template': notification_template,
            'context': {
                'msg_subject': f'Thank you for participating in the study titled {session.experiment.title}!'
            },
            'datetime': session.end,
        })

        # Create additional notifications for the next experiment day
        if next_experiment:
            # Get the experiment order in the study of this experiment
            next_experiment_order = next_experiment.studyxexperiment_set.first().experiment_order

            # Create a notification to be sent at 5:30 AM (localtime) on the next experiment day, 
            # containing a link for starting the next experiment
            
            # Get our session's timezone info
            # NOTE: Can this be moved to the Session model?
            session_tz = session.timezone
            if not session_tz:
                session_tz = 'UTC'

            session_tzinfo = zoneinfo.ZoneInfo(session_tz)

            target_time = timezone.datetime.combine(tomorrow, earliest_start_time, tzinfo=session_tzinfo)

            notification_list.append({
                'session': session,
                'template': notification_template,
                'context': {
                    'msg_number': len(notification_list)+1,
                    'msg_subject': f"Day {next_experiment_order} Study Reminder",
                    'curr_experiment_order': curr_experiment_order,
                    'prolific_study_name': next_experiment_ticket.experiment.title,
                    'ticket': next_experiment_ticket,
                },
                'datetime': target_time,
            })

            # Create a reminder notification to be sent at 6 PM (localtime) on the next experiment day.
            time = datetime.time(18,00)
            target_time = timezone.datetime.combine(tomorrow, time, tzinfo=session_tzinfo)

            # Generate the notification
            notification_list.append({
                'session': session,
                'template': notification_template,
                'context': {
                    'msg_number': len(notification_list)+1,
                    'msg_subject': f"Day {next_experiment_order} FINAL PARTICIPATION REMINDER ",
                    'prolific_study_name': next_experiment_ticket.experiment.title,
                    'ticket': next_experiment_ticket,
                },
                'datetime': target_time,
            })

        # Generate the notifications
        notifications = create_notifications(session, notification_list)

    return


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

                # Render the response through the PyEnsemble message interface
                msg = f"Prolific ID {prolific_id} has been added to the allow list for the study titled, {study['name']}."
            
            return render(request, 'pyensemble/message.html', {'msg': msg})

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

    return render(request, 'pyensemble/message.html', {'msg': msg})

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
        # This will delete the following objects:
        # 'pyensemble.FormXQuestion'
        # 'pyensemble.Form'
        # 'pyensemble.Question'
        # 'pyensemble.DataFormat'
        # 'pyensemble.Response'
        # 'pyensemble.FormXAttribute'
        # 'pyensemble.ExperimentXForm'

        pdb.set_trace()
        experiment.delete()

    # Delete the PyEnsemble study
    Study.objects.filter(title=params['pyensemble_study_title']).delete()

    msg = "Deleted the PyEnsemble study."

    return render(request, 'pyensemble/message.html', {'msg': msg})