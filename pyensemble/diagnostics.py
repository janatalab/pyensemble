# diagnostics.py
import json
import pandas as pd
import numpy as np

from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest

from pyensemble.models import Study, Session
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

            # Get the study data
            studydata = get_study_data(study, **kwargs)

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
def get_study_data(study, **kwargs):

    sxe_list = study.studyxexperiment_set.all().order_by('experiment_order')

    studydata = {
        'study': study.title,
        'experiment_data': []
    }

    for idx, sxe_item in enumerate(sxe_list):
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
        experiment_data = json.loads(response.content)

        # Extract the session data
        session_data = experiment_data['session_data']

        # Create our multiindex
        fields = session_data[0].keys()
        colindex = pd.MultiIndex.from_product([[experiment.title],fields], names=['experiment','details'])

        # Convert to Pandas dataframe
        df = pd.DataFrame(session_data)

        # Set the index
        df.index = experiment_data['subjects']

        # Set the columns
        df.columns = colindex

        # Append the dataframe
        studydata['experiment_data'].append(df)

    # Join the dataframes together
    studydata['experiment_data'] = studydata['experiment_data'][0].join(studydata['experiment_data'][1:])

    # Get column-level statistics that we want to communicate to the client
    studydata['experiment_data'] = studydata['experiment_data'].fillna(value=np.nan)

    studydata['stats'] = {
        'min': studydata['experiment_data'].min().to_json(orient='index'),
        'max': studydata['experiment_data'].max().to_json(orient='index'),
        'mean': studydata['experiment_data'].mean().to_json(orient='index'),
        'median': studydata['experiment_data'].median().to_json(orient='index'),
    }

    # Convert to json
    studydata['experiment_data'] = studydata['experiment_data'].to_json(orient='index')

    return studydata


def get_experiment_data(experiment, **kwargs):
    # There is a bit of tension here whether to return data organized by session or by subject. For most use cases, subject makes more sense.
    data = {'experiment': experiment.title}

    organize_by = kwargs.get('organize_by', 'subject')

    sessions = experiment.session_set.filter(exclude=False)

    if organize_by == 'session':
        # Iterate over sessions
        data.update({'session_data': []})

        for session in sessions:
            response = session.diagnostics(**kwargs)

            data['session_data'].append(json.loads(response.content))

    elif organize_by == 'subject':
        # Get the list of subjects
        subjects = sessions.values_list('subject__subject_id',flat=True).distinct()

        data.update({
            'subjects': list(subjects),
            'session_data': [],
            'num_sessions_per_subject': [],
            })

        # Iterate over subjects
        for subject in subjects:
            subject_sessions = sessions.filter(subject__subject_id=subject)

            # Note the number of sessions for this subject
            data['num_sessions_per_subject'].append((subject, subject_sessions.count()))

            # Only use the last session (this assumes previous sessions were failed attempts which may not always be a valid assumption)
            session = subject_sessions.last()

            # Run the diagnostics
            response = session.diagnostics(**kwargs)

            data['session_data'].append(json.loads(response.content))


    return JsonResponse(data)


@login_required
def exclude_session(request):
    if request.method == 'POST':
        session_ids = [json.loads(s) for s in request.POST.getlist('session_ids[]')]

        # Mark the sessions as excluded
        Session.objects.filter(pk__in=session_ids).update(exclude=True)

        # Fetch the study data anew
        study = Study.objects.get(title=request.POST['study'])
        studydata = get_study_data(study)

        return JsonResponse(studydata)

    else:
        return HttpResponseBadRequest()
