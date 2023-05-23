# reporting.py
from django.http import JsonResponse

import pdb

def default(session, *args, **kwargs):
    data = {}
    
    # Basic subject reporting
    data['subject_id'] = session.subject.subject_id

    data['subject_name'] = f"{session.subject.name_first} {session.subject.name_last}"

    # Basic session reporting
    data['session_id'] = session.id
    data['begin'] = session.start.strftime("%m/%d/%y %H:%M:%S") 
    data['end'] = session.end

    if data['end']:
        data['end'] = data['end'].strftime("%m/%d/%y %H:%M:%S")

    data['duration_min'] = None
    if data['end']:
        duration = (session.end - session.start).seconds/60
        data['duration_min'] = duration

    # Last form with response
    last_response = session.response_set.order_by('response_order').last()

    if last_response:
        data['response_order'] = last_response.response_order
        data['last_form'] = last_response.form.name

    return JsonResponse(data)