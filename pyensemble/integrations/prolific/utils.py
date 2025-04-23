# prolific.utils.py
import json

from django.http import HttpResponseBadRequest

from pyensemble.models import Subject, Session

from .prolific import Prolific

import pdb

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

        pdb.set_trace()

        # Now we need to get the study ID from the submission
        study_id = submission['study_id']

        # Now we can get the study
        study = prolific.get_study_by_id(study_id)

        # Now we can consult our completion codes

        # By default, use the completion code associated with "MANUALLY_REVIEW" action.
        



    