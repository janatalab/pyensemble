# tasks.py

from pyensemble.models import Experiment, ExperimentXForm, Subject

from django.urls import reverse
from django.shortcuts import render

import pdb

def get_expsess_key(experiment_id):
    return f'experiment_{experiment_id}'

def reset_session(request, experiment_id):
    expsess_key = get_expsess_key(experiment_id)
    expsessinfo = request.session.get(expsess_key)

    if not expsessinfo:
        msg = f'Experiment {experiment_id} session not initialized'
    else:
        msg = f'Experiment {experiment_id} session reset'
        request.session[expsess_key] = {}

    return render(request,'pyensemble/message.html',{'msg':msg})

def fetch_subject_id(subject, scheme='nhdl'):
    subject_id=None
    exists = False
    last = subject['name_last'].lower()
    first = subject['name_first'].lower()
    dob = subject['dob']

    # Check existence based on first and last name
    subjects = Subject.objects.filter(name_last__iexact=last, name_first__iexact=first, dob=dob)

    if subjects.count():
        if subjects.count() == 1:
            subject_id = subjects[0].subject_id
            exists = True
        else:
            raise ValueError('%d subjects with identical name and birthday'%(subjects.count()))
    else:
        if scheme=='nhdl':
            subject_id_root = str(dob.month)+last[0]+last[-1:]+first[0]+str(dob.year)[-2:]+str(dob.day)

            have_novel_id = False
            idnum = 0
            while not have_novel_id:
                idnum+=1
                subject_id = subject_id_root+str(idnum)

                subjects = Subject.objects.filter(subject_id=subject_id)

                if not subjects.count():
                    have_novel_id = True

        else:
            raise ValueError('unknown subject ID generator')

    return subject_id, exists


