# prolific.py
#
# Testing of PyEnsemble interactions with Prolific

from django.http import HttpResponse

from pyensemble.models import DataFormat, Question, Form, FormXQuestion, Experiment, ExperimentXForm, Study
from pyensemble.study import create_experiment_groupings

from pyensemble.integrations.prolific.prolific import Prolific

from pyensemble.models import Ticket
from pyensemble.tasks import create_tickets

import pdb


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
def create_example(request):
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

        # Check whether our experiment description is set
        if not experiment.description:
            # Add a description to the experiment
            experiment.description = f"This is a test of a multi-day study run via Prolific. This is Day {idx}."

        # Set our postsession callback
        if not experiment.post_session_callback:
            experiment.post_session_callback = f"debug.prolific.postsession_day{idx}"

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
        # Check whether the study already exists in Prolific in the project
        prolific_study = prolific.get_study(experiment.title, project_id=project['id'])

        if prolific_study:
            prolific_study_ids.append(prolific_study['id'])
            continue

        # If the study does not exist, make sure we have the required parameters
        
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

        # 11/16/2024: The completion codes specification is not working as expected, possibly due to a bug in the Prolific API
        # Try setting completion codes to None. Did not work.
        # prolific_study_params.update({
        #     'completion_codes': [{"code": None}]
        # })

        # 11/19/2024: Created studies manually in the Prolific UI.

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
        next_experiment = experiment.studyxexperiment_set.first().next()

        if next_experiment:
            # Create the participant group if necessary for the next experiment
            prolific.get_or_create_group(next_experiment.title)

    # Create the study collection 
    prolific.get_or_create_study_collection(pyensemble_study_title, prolific_study_ids)

    return HttpResponse("Success")

# Postsession callback for Day 1
def postsession_day1(request, *args, **kwargs):
    # Get the session
    session = kwargs['session']

    # Run any quality control checks
    passed_qc = True

    # Add checks here

    if not passed_qc:
        # Note that quality control failed
        return {'qc_failed': True}
    
    # Since we are dealing with a Prolific session, 
    # we need to add this participant to the eligibility list for the next study in the sequence.

    # Create a user ticket for the next experiment
    next_experiment = session.experiment.studyxexperiment_set.first().next()

    if next_experiment:
        pass

    #
    # Generate our notifications
    #

    # Create a list of dictionaries with notification parameters
    notification_list = []

    # Create a thank you notification, that contains a reminder about the next experiment day


    # Create a notification to be sent at  6:00 AM (localtime) on the next experiment day, 
    # containing a link for starting the next experiment


    # Create a reminder notification to be sent at 6 PM (localtime) on the next experiment day.


    # Generate the notifications
    notifications = create_notifications(session, notification_list)


# Postsession callback for Day 2
def postsession_day2(request, *args, **kwargs):
    pass

# Postsession callback for Day 3
def postsession_day3(request, *args, **kwargs):
    pass