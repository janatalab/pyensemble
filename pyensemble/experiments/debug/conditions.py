# conditions.py

from pyensemble.models import Session, Response

def desire_further_participation(request, *args, **kwargs):
    # Get the participant's session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our response
    response = Response.objects.get(session=session, question__text='I would like to be prompted with another participation opportunity.').response_value()

    return response == 'Yes'
