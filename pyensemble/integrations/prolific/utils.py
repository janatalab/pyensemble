# prolific.utils.py
import json

from django.conf import settings
from django.http import HttpResponseBadRequest

from pyensemble.models import Subject, Session

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

    