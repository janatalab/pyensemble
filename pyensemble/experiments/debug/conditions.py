# conditions.py

from pyensemble.models import Session, Response

def desire_further_participation(request, *args, **kwargs):
    # Get the participant's session ID
    session_id = kwargs['session_id']

    # Check if there is a question text parameter
    question_text = kwargs.get('question_text', 'I would like to be prompted with another participation opportunity.')

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Get our response
    response = Response.objects.get(session=session, question__text=question_text).response_value()

    return response == 'Yes'


def abort_participation(request, *args, **kwargs):
    # Get the participant's session ID
    session_id = kwargs['session_id']

    # Get our session
    session = Session.objects.get(pk=session_id)

    # Check if there is a question text parameter
    question_text = kwargs.get('question_text', None)

    response = None
    if question_text:
        response = Response.objects.get(session=session, question__text=question_text).response_value()

    else:
        question_text = kwargs.get('question_text_contains', None)

        if question_text:
            response = Response.objects.get(session=session, question__text__contains=question_text).response_value()

    if not response:
        return False
    
    else:
        return response == 'No'