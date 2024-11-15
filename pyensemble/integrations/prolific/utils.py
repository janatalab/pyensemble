# prolific.utils.py

from django.http import HttpResponseBadRequest

from pyensemble.models import Subject

def get_or_create_prolific_subject(request):
    # Get the Prolific ID
    prolific_id = request.GET.get('PROLIFIC_PID', None)

    # Make sure the parameter was actually specified
    if not prolific_id:
        return HttpResponseBadRequest('No Profilic ID specified')

    # Get or create a subject entry
    subject = Subject.objects.get_or_create(subject_id=prolific_id, id_origin='PRLFC')

    return subject
