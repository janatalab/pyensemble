# prolific.utils.py
import json

from django.conf import settings
from django.http import HttpResponseBadRequest

from pyensemble.models import Subject, Session
from pyensemble.utils import parsers, qc
import pyensemble.tasks as pt

from .prolific import Prolific

import pdb

# Start a logger
import logging
logger = logging.getLogger(__name__)

def get_participant_id(request):
    return request.GET.get('PROLIFIC_PID', None)


def get_study_id(request):
    return request.GET.get('STUDY_ID', None)


def get_or_create_prolific_subject(request):
    # Get the Prolific ID
    prolific_id = get_participant_id(request)

    # Make sure the parameter was actually specified
    if not prolific_id:
        return HttpResponseBadRequest('No Profilic ID specified')

    # Get or create a subject entry
    # We can't specify more info than the subject ID because the table is encrypted
    subject, created = Subject.objects.get_or_create(subject_id=prolific_id)

    # Update the entry with additional information if it was created
    if created:
        subject.id_origin='PRLFC'
        subject.email=f"{prolific_id}@email.prolific.com"

        # Now save the changes
        subject.save()

    return subject, created


def is_valid_participant(request):
    # Get the Prolific ID
    prolific_id = get_participant_id(request)

    # Make sure the parameter was actually specified
    if not prolific_id:
        return False

    # Get the study ID
    study_id = get_study_id(request)

    # Make sure the parameter was actually specified
    if not study_id:
        return False
    
    # Get a Prolific object
    prolific = Prolific()

    study = prolific.get_study_by_id(study_id)

    # Now get the participant group whose name matches that of the study
    group = prolific.get_group_by_name(study['name'])

    # If there is no group, we assume that no group membership is required and the participant is valid
    if not group:
        return True
    
    # Get the participant's group membership
    in_group = prolific.is_group_member(group['id'], prolific_id)

    # Return whether the participant is in the group
    return in_group


def default_completion_codes():
    # Create some completion code objects
    completion_codes = [
        {
            "code": "PYDEF",
            "code_type": "DEFAULT",
            "actor": "participant",  # This is the default actor. This means that the participant will be the one to complete the submission.
            "actions": [
                {
                    "action": "MANUALLY_REVIEW"
                }
            ]
        },
        {
            "code": "PYCMR",
            "code_type": "COMPLETED_MANUALLY_REVIEW",
            "actor": "researcher", # This means that the submission will be programmatically transitioned
            "actions": [
                {
                    "action": "MANUALLY_REVIEW"
                }
            ]
        },
        {
            "code": "PYIMR",
            "code_type": "INCOMPLETE_MANUALLY_REVIEW",
            "actor": "researcher", # This means that the submission will be programmatically transitioned
            "actions": [
                {
                    "action": "MANUALLY_REVIEW"
                }
            ]
        },
        {
            "code": "QFNS",
            "code_type": "QUALIFIED_FOR_NEXT_STUDY",
            "actor": "researcher",  
            "actions": [
                {
                    "action": "MANUALLY_REVIEW"
                },
            ],
        },
        {
            "code": "PYCAP",
            "code_type": "COMPLETED_APPROVE",
            "actor": "researcher",
            "actions": [
                {
                    "action": "AUTOMATICALLY_APPROVE"
                }
            ]
        },
        {
            "code": "PYCNM",
            "code_type": "CRITERIA_NOT_MET",
            "actor": "researcher",
            "actions": [
                {
                    "action": "REQUEST_RETURN",
                    "return_reason": "One or more criteria for participation were not met."
                }
            ]
        },
        {
            "code": "TKTNYV",
            "code_type": 'TICKET_NOT_YET_VALID',
            "actor": "researcher",
            "actions": [
                {
                    "action": "REQUEST_RETURN",
                    "return_reason": "The ticket is not yet valid."
                }
            ]
        },
        {
            "code": "TKTEXP",   
            "code_type": 'TICKET_EXPIRED',
            "actor": "researcher",
            "actions": [
                {
                    "action": "REQUEST_RETURN",
                    "return_reason": "The ticket has expired."
                }
            ]
        },
        {
            "code": "TKTALU",
            "code_type": 'TICKET_ALREADY_USED',
            "actor": "researcher",
            "actions": [
                {
                    "action": "REQUEST_RETURN",
                    "return_reason": "The ticket has already been used."
                }
            ]
        },
        {
            "code": "TKTINV",
            "code_type": 'INVALID_TICKET',
            "actor": "researcher",
            "actions": [
                {
                    "action": "REQUEST_RETURN",
                    "return_reason": "The ticket is invalid."
                }
            ]
        },
        {
            "code": "TKTMIS",
            "code_type": 'USER_TICKET_MISSING',
            "actor": "researcher",
            "actions": [
                {
                    "action": "REQUEST_RETURN",
                    "return_reason": "There is no ticket for this user."
                }
            ]
        },
    ]

    return completion_codes


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
        'maximum_allowed_time': 60,
        'completion_codes': default_completion_codes(),
        'device_compatibility': ["desktop"],
        'submissions_config': {
            'max_submissions_per_participant': 1, # set to -1 for unlimited testing
        }
    }

    return default_study_params


def get_prolific_ticket(experiment, ticket_attribute_name='Prolific Test'):
    # Fetch any existing tickets for the experiment
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
        ticket = pt.create_tickets(ticket_request_data).first()
    
    else:
        ticket = tickets.first()

    return ticket


def get_external_study_url(ticket):
    pid_str = "{{%PROLIFIC_PID%}}"
    study_id_str = "{{%STUDY_ID%}}"
    session_id_str = "{{%SESSION_ID%}}"

    external_study_url = f"{ticket.url}&PROLIFIC_PID={pid_str}&STUDY_ID={study_id_str}&SESSION_ID={session_id_str}"
    return external_study_url


def get_completion_url(request, *args, **kwargs):
    completion_url = None

    # Extract the session from the request
    session_id = kwargs.get('session_id', None)

    if not session_id:
        return HttpResponseBadRequest('No session ID specified')
    
    session = Session.objects.get(id=session_id)

    if session.experiment.params:
        params = json.loads(session.experiment.params)

        # Check whether params are specified in a dictionary
        if isinstance(params, dict):
            # The completion URL should be one that does not automatically indicate successful completion,
            # but rather manual review. A postsession callback that has run suitable quality control checks
            # can then indicate successful completion.
            completion_url = params.get('prolific_completion_url', None)

    # If we still don't have a completion URL, try to get it from the Prolific study using the source session
    if not completion_url:
        # Get a Prolific object
        prolific = Prolific()

        # We need to fetch the submission based on the session's origin_sessid
        submission = prolific.get_submission_by_id(session.origin_sessid)

        # Now we need to get the study ID from the submission
        study_id = submission['study_id']

        # Now we can get the study
        study = prolific.get_study_by_id(study_id)

        # Find the default completion code
        completion_code = None
        for code in study['completion_codes']:
            if code['code_type'] == 'DEFAULT':
                completion_code = code
                break

        if settings.DEBUG:
            pdb.set_trace()

        # If we found the completion code, we can get the completion URL
        completion_url = "https://app.prolific.co/submissions/complete"

        if completion_code:
            completion_url += f"?code={completion_code['code']}"

    return completion_url
        

def complete_prolific_session(request, *args, **kwargs):
    ''' 
    Determine the completion code to use for the Prolific submission and transition it. 
    This function should only be used for determining the completion code.
    Any other tasks that need to be performed after the session is completed should be done in the postsession callback.
    '''
    # Initialize the context
    context = {}

    # Get our session
    session = Session.objects.get(pk=kwargs['session_id'])

    # Indicate whether the last non-conditional form with a question was completed
    reached_last_form = session.last_form_responded()

    # Get our Prolific object
    prolific = Prolific()

    # Get the Prolific submission
    submission = prolific.get_submission_by_id(session.origin_sessid)

    # Get the study ID from the submission
    study_id = submission['study_id']

    # Get the study
    study = prolific.get_study_by_id(study_id)

    # Determine whether this experiment is in a sequence of experiments,
    # and, if so, whether this is the last experiment in the sequence.
    if not session.experiment.studyxexperiment_set.exists():
        # If there are no studyxexperiment entries, we assume that this is not a sequence of experiments.
        is_last_experiment = True

    else:
        # Get the studyxexperiment object for the current session's experiment
        sxe = session.experiment.studyxexperiment_set.first()

        # Determine whether this is the last experiment in the sequence
        is_last_experiment = sxe.experiment_order == sxe.study.num_experiments

    # See whether a quality control callback was provided
    if 'qc_callback' in kwargs:
        # If a quality control callback was provided, use it
        qc_check_callback = kwargs['qc_callback']

        # Parse the callback to get the quality control check function
        funcdict = parsers.parse_function_spec(qc_check_callback)

        # Get our selection function
        qc_check = parsers.fetch_experiment_method(funcdict['func_name'])

        # Add any additional arguments to the function call arguments
        kwargs.update(funcdict['kwargs'])

    else:
        # Otherwise, use the default quality control check
        qc_check = qc.default_session_qc_check

    # Run any quality control checks
    passed_qc = qc_check(session, *args, **kwargs)

    # Determine the completion code to use
    if passed_qc:
        # If this is not the last experiment in the sequence, we need to use the FOLLOW_UP_STUDY completion code

        if not is_last_experiment:
            # Get the completion code to enroll the participant in the next experiment
            completion_code = next((code['code'] for code in study['completion_codes'] if code['code_type'] == 'QUALIFIED_FOR_NEXT_STUDY'), None)

        else:
            # If this is the last experiment in the sequence, we need to use the COMPLETED_APPROVE completion code
            completion_code = next((code['code'] for code in study['completion_codes'] if code['code_type'] == 'COMPLETED_APPROVE'), None)

    else:
        # Perhaps the criteria were not met for the participant to complete the experiment at this time
        # Get the last response
        last_response = session.response_set.last()

        # Get the experiment parameters
        if session.experiment.params:
            experiment_params = json.loads(session.experiment.params)
        else:
            experiment_params = {}

        # Extract the list of exit forms from the experiment parameters
        exit_forms = experiment_params.get('exit_forms', [])

        if not exit_forms:
            exit_forms = ['Return Later']

        if reached_last_form:
            # Use the default completion code
            completion_code = next((code['code'] for code in study['completion_codes'] if code['code_type'] == 'COMPLETED_MANUALLY_REVIEW'), None)

        elif last_response.form.name in exit_forms:
            # If the last response was to the "Return Later" form, we need to use the RETURN_LATER completion code
            completion_code = next((code['code'] for code in study['completion_codes'] if code['code_type'] == 'CRITERIA_NOT_MET'), None)

        else:
            completion_code = next((code['code'] for code in study['completion_codes'] if code['code_type'] == 'INCOMPLETE_MANUALLY_REVIEW'), None)
            
    # Transition the submission
    # We can only transition if the completion code has a 'researcher' actor associated
    # with it. If the completion code has a 'participant' actor associated with it, we need to use the
    # completion URL instead.
    context['prolific_submission'] = complete_submission(session.origin_sessid, completion_code=completion_code)

    # Clear out any unsent notifications for this experiment
    if passed_qc or reached_last_form:
        pt.clear_unsent_notifications(session)

    return context


def complete_submission(submission_id, completion_code=None, code_type=None):
    status = None

    # Get a Prolific object
    prolific = Prolific()

    # Get the submission
    submission = prolific.get_submission_by_id(submission_id)

    context = {
        'submission_status': status,
        'submission': submission,
    }

    if not submission:
        logger.error(f"Submission with ID {submission_id} not found")
        status =  "SUBMISSION_NOT_FOUND"

    # Check whether the submission is active
    if submission:
        if submission['status'] != 'ACTIVE':
            logger.info(f"Submission with ID {submission_id} is not active")
            status =  "SUBMISSION_NOT_ACTIVE"
        
        else:
            # Figure out our completion code
            if not completion_code:
                # Get the completion codes for the submission from the study
                study = prolific.get_study_by_id(submission['study_id'])
                completion_codes = study['completion_codes']

                # Because we are trying to transition the submission programmatically,
                # we can only look at the completion codes that are meant for researchers
                completion_codes = [cc for cc in completion_codes if cc['actor'] == 'researcher']

                for cc in completion_codes:
                    # If we have a code type, we can use that to find the completion code
                    if (code_type and cc['code_type'] == code_type) or (not code_type and cc['code_type'] == 'COMPLETED_MANUALLY_REVIEW'):
                        completion_code = cc['code']
                        break

            # Now we can complete the submission
            curr_endpoint = prolific.api_endpoint+f"submissions/{submission_id}/transition/"

            data = {
                'action': 'COMPLETE',
                'completion_code': completion_code
            }

            # Make the request
            response = prolific.session.post(curr_endpoint, json=data).json()

            # Check the response
            if 'error' in response.keys():
                logger.error(f"Error completing submission: {response['error']}")
                status = "SUBMISSION_NOT_COMPLETED"

            else:
                status = "SUBMISSION_COMPLETED"
                submission = response

    context.update({
        'submission_status': status,
        'submission': submission,
    })

    return context


def approve_previous_submissions(session):
    # This is used in the context of a multi-study sequence
    # where we want to credit the previous submissions of the participant

    # Get a Prolific object
    prolific = Prolific()

    # Get studyxexperiment object for the current session
    sxe = session.experiment.studyxexperiment_set.first()

    # Loop over the experiments in the sequence
    while sxe.prev_experiment():
        # Get the previous experiment in the sequence
        prev_experiment = sxe.prev_experiment()

        # Get the sessions for the previous experiment.
        # Should just be one session, if a participant can only participate once per experiment. 
        # However, during testing, or if a participant had to exit early,
        # multiple sessions may have been created for the same experiment and same subject.
        prev_sessions = session.subject.session_set.filter(experiment=prev_experiment)

        # Loop over the sessions
        for prev_session in prev_sessions:
            # Get the Prolific submission
            prev_submission = prolific.get_submission_by_id(prev_session.origin_sessid)

            # Check the status of the submission
            if prev_submission['status'] == 'APPROVED':
                # If the submission is already approved, we don't need to do anything
                continue

            # It would be prudent to check on the completion code for that study
            # and only approve those with a completion code of QUALIFIED_FOR_NEXT_STUDY
            if prev_submission['status'] == 'AWAITING REVIEW':
                if prev_submission['study_code'] == 'QFNS':
                    # Now approve the submission
                    prev_submission = prolific.approve_submission(prev_session.origin_sessid)

                else:
                    continue

        sxe = prev_experiment.studyxexperiment_set.first()

    return True
