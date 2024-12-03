# prolific.utils.py

from django.http import HttpResponseBadRequest

from pyensemble.models import Subject

from .prolific import Prolific


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
    subject = Subject.objects.get_or_create(subject_id=prolific_id, id_origin='PRLFC')

    return subject


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

    # Generate the study endpoint
    api_endpoint = f"{prolific.api_endpoint}/studies/{study_id}/"

    study = prolific.session.get(api_endpoint)

    # Now get the participant group whose name matches that of the study
    group = prolific.get_group_by_name(study['name'])

    # If there is no group, we assume that no group membership is required and the participant is valid
    if not group:
        return True
    
    # Get the participant's group membership
    in_group = prolific.is_group_member(group['id'], prolific_id)

    # Return whether the participant is in the group
    return in_group
