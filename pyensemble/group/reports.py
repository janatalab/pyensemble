# reports.py

from django.contrib.auth.decorators import login_required

from pyensemble.group.models import GroupSession, GroupSessionSubjectSession
from pyensemble.models import Experiment, Response

from django.urls import reverse
from django.shortcuts import render
from django.http import JsonResponse

import pandas as pd

import pdb

@login_required
def home(request):
    template = "group/report/base.html"

    context = {
        'studies': [], # deal with this later
        'experiments': Experiment.objects.filter(is_group=True),
        'group_urls': {
            'experiment-session-selector': reverse('pyensemble-group:experiment-session-selector'),
            'experiment-analysis-nav': reverse('pyensemble-group:experiment-analysis-nav'),
            'session-detail': reverse('pyensemble-group:session-detail'),
            'exclude-groupsession': reverse('pyensemble-group:exclude_groupsession'),
        }
    }

    return render(request, template, context)

@login_required
def session_selector(request):
    pk = request.GET['id']

    if not pk:
        return HttpResponseRedirect(reverse('pyensemble-group:report'))

    template = "pyensemble/selectors/selector.html"

    context = {
        'level': 'session',
        'options': GroupSession.objects.filter(experiment__id=pk)
    }

    return render(request, template, context)

@login_required
def session_detail(request):
    template = "group/report/session_detail.html"

    pk = request.GET['id']

    # Get the list of subject sessions that were attached to this group session
    subject_sessions = GroupSessionSubjectSession.objects.filter(group_session=pk).values_list('user_session',flat=True)

    # Get all of the responses and order them by response order
    responses = Response.objects.filter(session_id__in=subject_sessions).order_by("response_order")

    # Convert to a Pandas dataframe
    df = pd.DataFrame(list(responses.values()))

    # We now want to rearrange the dataframe so that rows are indexed with response order and columns are a multi-level index corresponding to the subject at the top level and desired variables as the second level

    # pdb.set_trace()
    # df.loc[df['form_question_num']==0].pivot(index=['response_order'],columns=['subject_id'],values=['trial_info'])

    context = {}

    return render(request, template, context)


@login_required
def experiment_summary(request):
    # Only provide information about groups with attached participants
    # We ultimately want to add a "populated" attribute to the GroupSession model that returns objects that have populated sessions
    # We can also get our list of sessions from the GroupSessionSubjectSession
    gsss_set = GroupSessionSubjectSession.objects.filter(group_session__experiment__id=request.GET['experiment_id'])

    # Extract the unique group_sessions
    group_sessions = gsss_set.values_list('group_session', flat=True).distinct()

    # pdb.set_trace()

    experiment_data = {}

    return JsonResponse(experiment_data)

@login_required
def experiment_sessions(request):
    # Only provide information about groups with attached participants
    # We ultimately want to add a "populated" manager to the GroupSession model that returns objects that have populated sessions

    # We can also get our list of sessions from the GroupSessionSubjectSession
    gsss_set = GroupSessionSubjectSession.objects.filter(group_session__experiment__id=request.GET['experiment_id'])

    # Extract the unique group_sessions
    group_sessions = gsss_set.values_list('group_session', flat=True).distinct()

    # Get the sessions for our experiment. Only include those for which the exclude flag is not set
    sessions = GroupSession.objects.filter(pk__in=group_sessions, exclude=False)

    # Extract our values into a list
    # session_values = sessions.values('id','start_datetime','notes')

    # Loop over our session values list and insert session subjects
    # TODO: sort our dicts
    session_list = []

    for session in sessions:
        session_info = {}

        session_info['id'] = session.id
        session_info['start'] = session.start
        session_info['notes'] = session.notes
        session_info['subjects'] = []

        # Associate the subject sessions
        for gsss in gsss_set.filter(group_session=session.id):
            subject_session = gsss.user_session

            subject_info = {
                'subject_id': subject_session.subject.subject_id,
                'session_id': subject_session.id,
                # 'responses': [r for r in subject_session.response_set.values()]
            }

            # Evaluate the post-session callback
            if subject_session.response_set.count():
                last_response = subject_session.response_set.last()
                subject_info['last_response'] = {
                    'response_order': last_response.response_order,
                    'form_name': last_response.form.name,
                    'question': last_response.question.text,
                }
            else:
                subject_info['last_response'] = None



            session_info['subjects'].append(subject_info)

        session_list.append(session_info)

        # # sess['subjects'] = [s for s in GroupSession.objects.get(id=sess['id']).groupsessionsubjectsession_set.values_list('user_session__subject_id',flat=True)]

        # # We should also pull the subject session ID
        # sess['subject_sessions'] = [s for s in GroupSession.objects.get(id=sess['id']).groupsessionsubjectsession_set.values_list('user_session__id',flat=True)]

        # subject_session_qs = Session.objects.filter(pk__in=sess['subject_sessions'])


        # # Get some information about each participant
        # for subject_session in sess['subject_sessions']:
        #     # Get the subject responses
        #     subject_responses = Response.objects.filter(session__in=subject_session)

        #     # Extract their last response
        #     last_response = subject_responses.last()

    outdict = {
        'sessions': session_list,
    }

    return JsonResponse(outdict)

@login_required
def experiment_responses(request):
    experiment_data = {}

    return JsonResponse(experiment_data)
