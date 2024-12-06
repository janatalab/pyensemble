# prolific.py
#
# Testing of PyEnsemble interactions with Prolific

import datetime
import zoneinfo

from django.utils import timezone
from django.http import HttpResponse

from pyensemble.models import DataFormat, Question, Form, FormXQuestion, Experiment, ExperimentXForm, Study, Notification
from pyensemble.study import create_experiment_groupings

from pyensemble.integrations.prolific.prolific import Prolific

from pyensemble.tasks import create_tickets, get_or_create_next_experiment_ticket, create_notifications

import pdb

date_format_str = '%A, %B %-d'

# Ultimately, remove this when the Prolific API bug is fixed
PROLIFIC_BUG_FIXED = False

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
        'study_name': "",
        'description': "",
        'external_study_url': "",
        'prolific_id_option': "url_parameters",
        'reward': 0,
        'total_available_places': 1,
        'estimated_completion_time': 1,
        'completion_codes': None,
        'device_compatibility': ["desktop"],
    }

    return default_study_params


# Create a wrapper for the integration example
def create_multiday_example(request):
    response = create_prolific_pyensemble_integration_example()

    return response


# Create a study
def create_prolific_pyensemble_integration_example():
    """
    Define some general parameters
    """
    prolific_project_title = "PyEnsemble Integration Testing" # Prolific project title

    # Define our PyEnsemble study title. This is also the Prolific study collection name.
    pyensemble_study_title = 'Prolific Multi-Day Study'

    """
    Deal with the PyEnsemble side of the Prolific integration.
    """

    # Define our experiment titles
    experiment_titles = [
            'Prolific Multi-Day Study - Day 1',
            'Prolific Multi-Day Study - Day 2',
            'Prolific Multi-Day Study - Day 3'
        ]
    
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
            'name': 'Start Session',
            'questions': [],
            'form_handler': 'form_subject_register'
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

        # Add the questions to the form
        for idx, q in enumerate(f['questions'], start=1):
            fqo, _ = FormXQuestion.objects.get_or_create(form=fo, question=q, form_question_num=idx)

        # Add the form to our form_instances QuerySet
        form_instances = form_instances | Form.objects.filter(id=fo.id)

    # Create the ExperimentXForm entries
    for idx, experiment in enumerate(experiment_titles, start=1):
        # Get the experiment object
        experiment = Experiment.objects.get(title=experiment)

        #
        # Set additional experiment parameters
        #

        # Add a description to the experiment
        experiment.description = f"This is a test of a multi-day study run via Prolific. This is Day {idx}."

        # Set our postsession callback
        experiment.post_session_callback = "debug.prolific.postsession(create_notifications=True)"

        # Set expectation of a user ticket if this is Day 2 or 3 experiment
        if idx in [2, 3]:
            experiment.user_ticket_expected = True

        # Save the experiment, even if nothing changed
        experiment.save()

        # Delete any existing ExperimentXForm entries for this experiment
        ExperimentXForm.objects.filter(experiment=experiment).delete()

        # Get the form objects
        if idx in [1, 2]:
            form_objs = form_instances.filter(name__in=['Start Session', f'Participate on Day {idx+1}', 'End Session'])
        else:
            form_objs = form_instances.filter(name__in=['Start Session', 'End Session'])

        # Create the ExperimentXForm entries
        for idx, form in enumerate(form_objs, start=1):
            ExperimentXForm.objects.get_or_create(
                experiment = experiment,
                form = form,
                form_order = idx
                )
            
    """
    Deal with the Prolific side of the Prolific integration.
    Note that what we refer to as an "experiment" in PyEnsemble is referred to as a "study" in Prolific.
    What we refer to as a "study" in PyEnsemble is referred to as a "study collection" in Prolific.

    The Prolific API: https://docs.prolific.com/docs/api-docs/public/
    """
    # Get ourselves a Prolific API object
    prolific = Prolific()

    # Create a project
    project, _ = prolific.get_or_create_project(prolific_project_title)

    # Intialize our list of Prolific study IDs
    prolific_study_ids = []

    # Create each Profilic study, i.e. corresponding to each PyEnsemble experiment
    for experiment in study.experiments.all():
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

        # Check whether the study already exists in Prolific in the project
        prolific_study = prolific.get_study(experiment.title, project_id=project['id'])

        if prolific_study:
            prolific_study_ids.append(prolific_study['id'])

        # If the study does not exist, make sure we have the required parameters before we try to create it.
        # NOTE: 11/16/2024: The completion codes specification is not working as expected, possibly due to a bug in the Prolific API
        # 11/19/2024: Created studies manually in the Prolific UI.
        # 12/04/2024: Automated study creation is still not working due to the completion codes issue and the 
        # fact that the completion codes are required for the study creation.

        if PROLIFIC_BUG_FIXED:               
            # Get the default study parameters
            prolific_study_params = get_default_prolific_study_params()

            # Update the study parameters with the experiment title
            prolific_study_params.update({
                'study_name': experiment.title,
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
            prolific_study_ids.append(prolific_study['id'])

        # Create a participant group for the next study, if applicable
        # Get the next experiment in the sequence
        next_experiment = experiment.studyxexperiment_set.first().next_experiment()

        if next_experiment:
            # Create the participant group if necessary for the next experiment
            prolific.get_or_create_group(next_experiment.title)

    # Create the study collection if we, in fact, have our full set of studies
    if len(prolific_study_ids) == study.num_experiments:
        prolific.get_or_create_study_collection(pyensemble_study_title, prolific_study_ids)

    return HttpResponse("Success")


# Create a single postsession callback that can be used for all days
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

            pdb.set_trace()
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