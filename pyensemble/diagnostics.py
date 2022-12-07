# diagnostics.py
import json
import pandas as pd

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

            # Join the dataframes together and convert to json
            studydata['experiment_data'] = studydata['experiment_data'][0].join(studydata['experiment_data'][1:]).to_json(orient='index')

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
    # There is a bit of tension here whether to return data organized by session or by subject. For most use cases, subject makes more sense.
    data = {'experiment': experiment.title}

    organize_by = kwargs.get('organize_by', 'subject')

    if organize_by == 'session':
        # Get the list of sessions
        sessions = experiment.session_set.all()

        # Iterate over sessions
        data.update({'session_data': []})

        for session in sessions:
            response = session.diagnostics(**kwargs)

            data['session_data'].append(json.loads(response.content))

    elif organize_by == 'subject':
        # Get the list of subjects
        subjects = experiment.session_set.values_list('subject__subject_id',flat=True).distinct()

        data.update({
            'subjects': list(subjects),
            'session_data': [],
            'num_sessions_per_subject': [],
            })

        # Iterate over subjects
        for subject in subjects:
            sessions = experiment.session_set.filter(subject__subject_id=subject)

            # Note the number of sessions for this subject
            data['num_sessions_per_subject'].append((subject, sessions.count()))

            # Only use the last session (this assumes previous sessions were failed attempts which may not always be a valid assumption)
            session = sessions.last()

            # Run the diagnostics
            response = session.diagnostics(**kwargs)

            data['session_data'].append(json.loads(response.content))


    return JsonResponse(data)
