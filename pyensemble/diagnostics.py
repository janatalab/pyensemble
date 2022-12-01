# diagnostics.py
import json

from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest

from pyensemble.models import Study
from pyensemble.forms import StudySelectForm

import pdb

# Diagnostics views
#

@login_required
def index(request, *args, **kwargs):
    template = "pyensemble/diagnostics/base.html"
    context = {}
    return render(request,template,context)


@login_required
def study(request, *args, **kwargs):
    if request.method == 'POST':
        form = StudySelectForm(request.POST)

        if form.is_valid():
            # Get the study
            study = Study.objects.get(title=form.cleaned_data['study'])

            sxe_list = study.studyxexperiment_set.all().order_by('experiment_order')

            studydata = {
                'study': study.title,
                'data': []
            }

            for sxe_item in sxe_list:
                # Get our experiment object
                experiment = sxe_item.experiment

                # Make sure we have an associated diagnostics script
                # May want to have this error-checking elsewhere
                if not experiment.session_diagnostic_script:
                    return HttpResponseBadRequest(f"No diagnostics script associated with {experiment.title}")

                # Call the experiment method to aggregate data for the experiment
                response = get_experiment_data(experiment)

                # NOTE: We need to do some dataframe joining here on the subject indices so that we end up with a single dataframe. 
                # NOTE: Need to handle case in which a participant may have initiated multiple sessions for a single experiment.


                studydata['data'].append(json.loads(response.content))


            return JsonResponse(studydata)

    else:
        form = StudySelectForm()

    context = {
        'form': form,
    }

    template = "pyensemble/diagnostics/study.html"
    return render(request, template, context)


@login_required
def experiment(request, *args, **kwargs):
    pass


@login_required
def session(request, *args, **kwargs):
    pass

# The study, experiment, and session views ultimately are all expected to redirect to views that return JSON data that correspond to elements in a Pandas DataFrame

def get_experiment_data(experiment, **kwargs):
    # Get the list of sessions
    sessions = experiment.session_set.all()

    # Iterate over sessions
    data = {
        'experiment': experiment.title,
        'session_data': [],
    }
    for session in sessions:
        response = session.diagnostics(**kwargs)

        data['session_data'].append(json.loads(response.content))

    return JsonResponse(data)
