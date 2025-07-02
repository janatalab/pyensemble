# reporting.py

'''
These are template reporting functions that are used by default by the reporting method 
associated with the AbstractSession model in pyensemble.models and 
the get_experiment_data method in pyensemble.reporting
'''

import json

from django.http import JsonResponse

from pyensemble.group.models import GroupSession

import pdb

def default(session, *args, **kwargs):
    session_data = {}

    # Basic session reporting
    session_data['session_id'] = session.id
    session_data['start'] = session.start.strftime("%m/%d/%y %H:%M:%S") 
    session_data['end'] = session.end

    if session_data['end']:
        session_data['end'] = session_data['end'].strftime("%m/%d/%y %H:%M:%S")

    session_data['duration_min'] = None
    if session_data['end']:
        duration = (session.end - session.start).seconds/60
        session_data['duration_min'] = duration

    if session.experiment.is_group:
        # Are we getting data at the group level or individual subject level
        if isinstance(session, GroupSession):
            # Get our subject sessions for this group session
            subject_sessions = session.groupsessionsubjectsession_set.all()

            subject_session_data = {}

            # Basic group session reporting
            session_data['subject_session_data'] = subject_session_data
            session_data['notes'] = session.notes
            session_data['files'] = [f for f in session.groupsessionfile_set.values_list('file', flat=True)]

            session_data['meta'] = {
                'all_completed': subject_sessions.all_completed()
            }

            # Associate the subject sessions
            for gsss in subject_sessions:
                subject_session = gsss.user_session

                # Fetch the session data via the reporting mechanism
                response = subject_session.reporting(**kwargs)

                # Update our directory
                subject_session_data.update({subject_session.id: json.loads(response.content)})

                # subject_data = get_subject_data(subject_session)
                # subject_data.update({'session_id', subject_session.id})

                # session_data['session_data'].append(subject_data)
        else:
            session_data.update(get_subject_data(session, **kwargs))

    else:
        session_data.update(get_subject_data(session, **kwargs))

    return JsonResponse(session_data)


def get_subject_data(session, *args, **kwargs):
    subject_data = {}

    # Basic subject reporting
    subject_data['subject_id'] = session.subject.subject_id

    subject_data['subject_name'] = f"{session.subject.name_first} {session.subject.name_last}"

    # Last form with response
    if session.response_set.count():
        last_response = session.response_set.order_by('response_order').last()

        subject_data['last_response'] = {
            'response_order': last_response.response_order,
            'form_name': last_response.form.name,
            'question': last_response.question.text,
        }
    else:
        subject_data['last_response'] = None

    # Get the completion time statistics for the session
    # subject_data['form_completion_time_stats'] = session.response_set.all().form_completion_time_statistics()


    return subject_data

