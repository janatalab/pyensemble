# reporting.py
from django.http import JsonResponse

def default(session, *args, **kwargs):
    data = {}

    # Basic subject reporting
    data['subject_id'] = session.subject.subject_id

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

    return JsonResponse(data)