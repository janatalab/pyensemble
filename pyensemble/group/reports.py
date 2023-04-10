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
    experiment_data = {}

    return JsonResponse(experiment_data)