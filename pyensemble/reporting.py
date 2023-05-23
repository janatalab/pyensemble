# reporting.py
import os
import json
import pandas as pd
import numpy as np

from django.contrib.auth.decorators import login_required

from django.db.models import Max

from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest

from pyensemble.models import Study, Session, Experiment
from pyensemble import forms

import pdb

#
# Reporting views
#

template_base = "pyensemble/reporting"

@login_required
def index(request, *args, **kwargs):
    template = os.path.join(template_base, "base.html")
    context = {}
    return render(request,template,context)


@login_required
def study(request, *args, **kwargs):
    if request.method == 'POST':
        form = forms.StudySelectForm(request.POST)

        if form.is_valid():
            # Get the study
            study = Study.objects.get(title=form.cleaned_data['study'])

            # Get the study data
            studydata = get_study_data(study, **kwargs)

            return JsonResponse(studydata)

    else:
        form = forms.StudySelectForm()

    context = {
        'form': form,
    }

    template = os.path.join(template_base, "study.html")
    return render(request, template, context)


@login_required
def experiment(request, *args, **kwargs):
    if request.method == 'POST':
        form = forms.ExperimentSelectForm(request.POST)

        if form.is_valid():
            title = form.cleaned_data['experiment']

            # Get the experiment
            experiment = Experiment.objects.get(title=title)

            # Get the experiment data
            kwargs.update({'package': True})
            data = get_experiment_data(experiment, **kwargs)

            return JsonResponse(data)
    else:
        filters = {
            # 'exclude': {'session_reporting_script':''},
            'exclude': {},
            'filter': {}
        }
        form = forms.ExperimentSelectForm(**filters)

    context = {
        'form': form,
    }

    template = os.path.join(template_base, "experiment.html")
    return render(request, template, context)


@login_required
def experiment_summary(request, *args, **kwargs):
    pass


@login_required
def experiment_responses(request, *args, **kwargs):

    if request.method == 'POST':
        form = forms.ExperimentResponsesForm(request.POST)

        if form.is_valid():
            # Fetch our responses according to the specified criteria
            pdb.set_trace()
            experiment_responses = Response.objects.filter(
                experiment=form.cleaned_data['experiment'],
                question__in=form.cleaned_data['question'],
            )

            if form.cleaned_data['filter_excluded']:
                experiment_responses.exclude(exclude=True)

            if form.cleaned_data['filter_unfinished']:
                experiment_responses.exclude(session__end_datetime__isnull=True)

            # Perform any further ordering of the responses

            # Generate our list of columns

            return render(request, "pyensemble/reporting/experiment_responses.html", context)

    else:
        experiment_id = request.GET['experiment_id']

        # Get our response selection form
        form = forms.ExperimentResponsesForm(initial={'experiment': experiment_id})

        context = {
            'experiment': Experiment.objects.get(pk=experiment_id),
            'form': form,
        }


    template = "pyensemble/reporting/select_reporting_parameters.html"
    return render(request, template, context)


@login_required
def session(request, *args, **kwargs):
    pass


# The study, experiment, and session views ultimately are all expected to redirect to views that return JSON data that correspond to elements in a Pandas DataFrame
def get_study_data(study, **kwargs):

    sxe_list = study.studyxexperiment_set.all().order_by('experiment_order')

    studydata = {
        'title': study.title,
        'experiment_data': []
    }

    for idx, sxe_item in enumerate(sxe_list):
        # Get our experiment object
        experiment = sxe_item.experiment

        # Make sure we have an associated reporting script
        # May want to have this error-checking elsewhere
        if not experiment.session_reporting_script:
            return HttpResponseBadRequest(f"No reporting script associated with {experiment.title}")

        # Call the experiment method to aggregate data for the experiment
        experiment_data = get_experiment_data(experiment)

        # NOTE: We need to do some dataframe joining here on the subject indices so that we end up with a single dataframe. 
        # NOTE: Need to handle case in which a participant may have initiated multiple sessions for a single experiment.

        df = convert_experiment_data_to_df(experiment_data)

        # Append the dataframe
        studydata['experiment_data'].append(df)

    # Join the dataframes together
    studydata['experiment_data'] = studydata['experiment_data'][0].join(studydata['experiment_data'][1:])

    # Get column-level statistics that we want to communicate to the client
    studydata['stats'], studydata['experiment_data'] = get_column_statistics(studydata['experiment_data'])

    # Now convert the experiment data to json
    studydata['experiment_data'] = studydata['experiment_data'].to_json(orient='index', double_precision=2)

    return studydata

def convert_experiment_data_to_df(experiment_data):
    # Extract the session data
    session_data = experiment_data['session_data']

    # Create our multiindex
    fields = session_data[0].keys()
    colindex = pd.MultiIndex.from_product([[experiment_data['experiment']],fields], names=['experiment','details'])

    # Convert to Pandas dataframe
    df = pd.DataFrame(session_data)

    # Set the index
    df.index = experiment_data['subjects']

    # Set the columns
    df.columns = colindex  
    
    return df  

def get_experiment_data(experiment, **kwargs):
    # There is a bit of tension here whether to return data organized by session or by subject. For most use cases, subject makes more sense.
    data = {'experiment': experiment.title}

    organize_by = kwargs.get('organize_by', 'subject')

    sessions = experiment.session_set.exclude(exclude=True)

    if organize_by == 'session':
        # Iterate over sessions
        data.update({'session_data': []})

        for session in sessions:
            response = session.reporting(**kwargs)

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
            num_subject_sessions = subject_sessions.count()
            data['num_sessions_per_subject'].append((subject, num_subject_sessions))

            # Only use the last session (this assumes previous sessions were failed attempts which may not always be a valid assumption)
            # It turns out that this is a poor assumption. We should look for complete sessions instead
            session = None
            if num_subject_sessions > 1:
                # Get a list of complete sessions
                complete_sessions = subject_sessions.filter(end_datetime__isnull=False)
                num_complete_sessions = complete_sessions.count()

                if num_complete_sessions == 1:
                    session = complete_sessions[0]

                elif num_complete_sessions > 1:
                    # Annotate each session with the maximum response_order value for that session
                    complete_sessions = complete_sessions.annotate(max_response_order=Max('response__response_order'))

                    # Get the max response_order value across sessions
                    max_value_obj = complete_sessions.aggregate(max_field=Max('max_response_order'))

                    # Select the object with the greatest value
                    session = complete_sessions.get(max_response_order=max_value_obj['max_field'])

            # If we did not find a session that ended cleanly, grab the last one
            if not session or not session.end:
                session = subject_sessions.last()

            # Run the reporting
            response = session.reporting(**kwargs)

            data['session_data'].append(json.loads(response.content))

    # Assign our output variable
    outdata = data

    # If this we aren't fetching as part of a study, then compute the stats and package the result
    if kwargs.get('package', False):
        # Confert to data frame
        df = convert_experiment_data_to_df(data)

        # We now need to package it into same format as we do for a study
        stats, df = get_column_statistics(df)

        outdata = {
            'title': experiment.title,
            'experiment_data': df.to_json(orient='index', double_precision=2),
            'stats': stats,
        }

    return outdata


def get_column_statistics(data):
    data = data.fillna(value=np.nan)

    stats = {
        'min': data.min().to_json(orient='index', double_precision=2),
        'max': data.max().to_json(orient='index', double_precision=2),
        'mean': data.mean().to_json(orient='index', double_precision=2),
        'median': data.median().to_json(orient='index', double_precision=2),
    }

    return stats, data


@login_required
def exclude_session(request):
    if request.method == 'POST':
        session_ids = [json.loads(s) for s in request.POST.getlist('session_ids[]')]

        # Mark the sessions as excluded
        Session.objects.filter(pk__in=session_ids).update(exclude=True)

        # Fetch the study data anew
        title = request.POST['title']
        level = request.POST['level']

        if level == 'study':
            study = Study.objects.get(title=title)
            data = get_study_data(study)

        elif level == 'experiment':
            experiment = Experiment.objects.get(title=title)
            data = get_experiment_data(experiment, package=True)

        return JsonResponse(data)

    else:
        return HttpResponseBadRequest()
