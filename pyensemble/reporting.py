# reporting.py
import os
import json
import pandas as pd
import numpy as np

from django.contrib.auth.decorators import login_required

from django.db.models import Max

from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest

from pyensemble.models import Study, Session, Experiment, StudyXExperiment
from pyensemble.group.models import GroupSession

from pyensemble.group import reports as group_report

from pyensemble import forms

import pdb

#
# Reporting views
#

template_base = "pyensemble/reporting"

@login_required
def index(request, *args, **kwargs):
    template = os.path.join(template_base, "base.html")

    context = {
        'studies': Study.objects.all(),
        'experiments': Experiment.objects.all(),
        'report_urls': {
            'study-analysis-nav': reverse('study-analysis-nav'),
            'experiment-analysis-nav': reverse('experiment-analysis-nav'),
            'experiment-session-selector': reverse('experiment-session-selector'),
            'exclude-session': reverse('session-exclude'),
            'exclude-subject': reverse('subject-exclude'),
            'attach-file': reverse('attach_session_file'),
        },
    }

    return render(request,template,context)


@login_required
def study(request, *args, **kwargs):
    if request.method == 'POST':
        form = forms.StudySelectForm(request.POST)

        if form.is_valid():
            # Get the study
            study = Study.objects.get(title=form.cleaned_data['study'])

            # Get the study data
            data = get_study_data(study, **kwargs)

            return JsonResponse(data)

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
def study_summary(request, *args, **kwargs):
    pass


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
        'type': 'study_data',
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
        experiment_data = get_experiment_data(experiment, **kwargs)

        # Convert our data to a Pandas dataframe for subsequent joining an calculation of stats
        df = convert_experiment_session_data_to_df(experiment_data)

        '''
        Because sessions are unique to an experiment, we're going to need to have 
        an index that we can join on. The only identifiers we can join on across 
        experiments are subject_id or group_id. Make sure we have such an index 
        and create if necessary.
        '''

        if not 'subject_id' in df.index.names:
            # Fetch our subject IDs
            subject_ids = df.index.map(lambda x: experiment.session_set.get(pk=x).subject_id)

            # Replace the old index
            df.set_index(subject_ids, inplace=True)

        # Append the dataframe
        studydata['experiment_data'].append(df)

    # Join the experiment dataframes together
    studydata['experiment_data'] = studydata['experiment_data'][0].join(studydata['experiment_data'][1:])

    # Get column-level statistics that we want to communicate to the client
    studydata['stats'], studydata['experiment_data'] = get_column_statistics(studydata['experiment_data'])

    # Now convert the experiment data to json
    try:
        studydata['experiment_data'] = studydata['experiment_data'].to_json(orient='index', double_precision=2)
    except:
        return ValueError("Subject sessions could not be joined across experiments. More than one session found for one or more subjects for one or more experiments in the study. Some sessions may need to be removed from individual experiments.")

    return studydata


def convert_experiment_session_data_to_df(experiment_data):
    # Extract the session data
    session_data = experiment_data['session_data']

    # Get our first entry
    first_entry = next(iter(session_data.items()))

    # Extract the column names
    fields = first_entry[1].keys()

    # Create a multiindex for the column names
    colindex = pd.MultiIndex.from_product([[experiment_data['experiment']['title']],fields], names=['experiment','variable'])

    # Convert to Pandas dataframe
    # Transpose so that subject_id, session_id tuple strings are the row indices
    df = pd.DataFrame(session_data).transpose()

    # Set the columns
    df.columns = colindex  

    if df.index.nlevels > 1:
        # Create a multiindex for the rows
        df.index = df.index.map(lambda x: tuple(x[1:-1].split(', ')))

        # Name the columns of the row multiindex
        df.index.rename(['subject_id','session_id'], inplace=True)
    else:
        df.index.name = 'session_id'

    return df  


def get_experiment_data(experiment, **kwargs):
    experiment_data = {
        'type': 'experiment_data',
        'experiment': {
            'id': experiment.id,
            'title': experiment.title,
            'is_group': experiment.is_group,
        },
        'session_data': {},
    }

    # Get our session data
    experiment_data['session_data'] = get_experiment_session_data(experiment, **kwargs)

    return experiment_data


# Define a method that runs per-session reporting and aggregates the session data
def get_experiment_session_data(experiment, **kwargs):
    # Initialize our session data
    session_data = {}

    # Get all our sessions
    sessions = experiment.session_set.all()

    # Exclude sessions flagged as such
    include_excluded = kwargs.get('include_excluded', False)
    if not include_excluded:
        sessions = sessions.exclude(exclude=True)

    for session in sessions:
        # Fetch the session data via the reporting mechanism
        response = session.reporting(**kwargs)

        # Update our directory
        session_data.update({session.id: json.loads(response.content)})

    return session_data

    # elif organize_by == 'subject':
    #     # Get the list of subjects
    #     subjects = sessions.values_list('subject__subject_id',flat=True).distinct()

    #     data.update({
    #         'subjects': list(subjects),
    #         'data': [],
    #         'num_sessions_per_subject': [],
    #         })

    #     # Iterate over subjects
    #     for subject in subjects:
    #         subject_sessions = sessions.filter(subject__subject_id=subject)

    #         # Note the number of sessions for this subject
    #         num_subject_sessions = subject_sessions.count()
    #         data['num_sessions_per_subject'].append((subject, num_subject_sessions))

    #         for session in subject_sessions:
    #             # Run the reporting
    #             response = session.reporting(**kwargs)

    #         if num_subject_sessions > 1:
    #             # Get a list of complete sessions
    #             complete_sessions = subject_sessions.filter(end_datetime__isnull=False)
    #             num_complete_sessions = complete_sessions.count()

    #             if num_complete_sessions == 1:
    #                 session = complete_sessions[0]

    #             elif num_complete_sessions > 1:
    #                 # Annotate each session with the maximum response_order value for that session
    #                 complete_sessions = complete_sessions.annotate(max_response_order=Max('response__response_order'))

    #                 # Get the max response_order value across sessions
    #                 max_value_obj = complete_sessions.aggregate(max_field=Max('max_response_order'))

    #                 # Select the object with the greatest value
    #                 session = complete_sessions.get(max_response_order=max_value_obj['max_field'])

    #         # If we did not find a session that ended cleanly, grab the last one
    #         if not session or not session.end:
    #             session = subject_sessions.last()

    #         # Run the reporting
    #         response = session.reporting(**kwargs)

    #         data['data'].append(json.loads(response.content))

    # Assign our output variable
    # outdata = data

    # # If we aren't fetching as part of a study, then compute the stats and package the result
    # if kwargs.get('package', False):
    #     # Confert to data frame
    #     df = convert_experiment_data_to_df(data)

    #     # We now need to package it into same format as we do for a study
    #     stats, df = get_column_statistics(df)

    #     outdata = {
    #         'title': experiment.title,
    #         'experiment_data': df.to_json(orient='index', double_precision=2),
    #         'stats': stats,
    #     }



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
        experiment = Experiment.objects.get(pk=request.POST['experiment'])

        session_id = request.POST['session']
        if experiment.is_group:
            session = GroupSession.objects.get(pk=session_id)
        else:
            session = Session.objects.get(pk=session_id)

        session.exclude = True
        session.save()

        return HttpResponse(f"Marked {session_id} for exclusion")

    else:
        return HttpResponseBadRequest()


@login_required
def exclude_subject(request):
    if request.method == 'POST':
        # Get our subject_id
        subject_id = request.POST['subject']

        # First try to see whether a study has been specified
        study = request.POST.get('study', None)

        if study:
            # Get a list of our subject sessions
            subject_sessions = Session.objects.filter(subject=subject_id, experiment__studyxexperiment__study=study)

        else:
            experiment = Experiment.objects.get(pk=request.POST['experiment'])

            if experiment:
                # Get the subject's sessions for this experiment
                subject_sessions = Session.objects.get(subject=subject_id, experiment=experiment)

        num_sessions = subject_sessions.update(exclude=True)

        return HttpResponse(f"Marked {num_sessions} of {subject_id} for exclusion")

    else:
        return HttpResponseBadRequest()


@login_required
def attach_session_file(request):
    if request.method == "POST":
        # Check whether we have a groupsession or session field
        if request.POST.get('groupsession', None):
            form_class = GroupSessionFileAttachForm
        else:
            form_class = SessionFileAttachForm

        # Populate the form
        form = form_class(request.POST, request.FILES)            

        if form.is_valid():
            # Save the file
            form.save()

            return HttpResponseRedirect(reverse('attach_session_file_success'))

    else:
        # Determine whether we are dealing with a group experiment
        experiment = Experiment.objects.get(pk=request.GET.get('experiment_id'))

        session_id = request.GET.get('session_id', None)

        if experiment.is_group:
            form = forms.GroupSessionFileAttachForm(initial={'groupsession': session_id})

        else:
            form = forms.SessionFileAttachForm(initial={'session': session_id})            
    context = {
        'form': form,
    }

    return render(request, "pyensemble/reporting/attach_session_file.html", context)


def attach_session_file_success(request):
    return HttpResponse("Successfully uploaded the session file")


@login_required
def study_sessions(request):
    # Extract our study ID
    study_id = request.GET['study']

    # Get our study instance
    study = Study.objects.get(pk=study_id)

    # Extract our data
    data = get_study_data(study)

    if isinstance(data, ValueError):
        return HttpResponseBadRequest(data.args[0])

    return JsonResponse(data)


@login_required
def experiment_session_selector(request):
    pk = request.GET['id']

    if not pk:
        return HttpResponseRedirect(reverse('reporting'))

    template = "pyensemble/selectors/selector.html"

    # Fetch the experiment
    experiment = Experiment.objects.get(pk=pk)

    # Fetch the sessions
    if experiment.is_group:
        sessions = experiment.groupsession_set.all()
    else:
        sessions = experiment.session_set.all()

    context = {
        'level': 'session',
        'options': sessions,
    }

    return render(request, template, context)


@login_required
def experiment_sessions(request):
    # Extract our experiment ID
    experiment_id = request.GET['experiment']

    experiment = Experiment.objects.get(pk=experiment_id)

    # Get the experiment session data
    experiment_data = get_experiment_data(experiment)

    # Return the response
    return JsonResponse(experiment_data)


