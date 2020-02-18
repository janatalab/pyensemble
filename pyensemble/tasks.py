# tasks.py

from pyensemble.models import Experiment, ExperimentXForm

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

def determine_next_form(request, experiment_id):
    next_formidx = None

    expsess_key = get_expsess_key(experiment_id)
    expsessinfo = request.session.get(expsess_key)

    # Get our form stack
    exf = ExperimentXForm.objects.filter(experiment=experiment_id).order_by('form_order')

    # Get our current form
    form_idx = expsessinfo['curr_form_idx']
    currform = exf[form_idx]

    check_conditional = True

    # See whether a break loop flag was set
    # pdb.set_trace()
    # break_loop = formset.cleaned_data['break_loop']
    break_loop = False

    # Fetch our variables that control looping
    num_repeats = exf[form_idx].repeat
    goto_form_idx = exf[form_idx].goto

    if break_loop:
        # If the user chose to exit the loop
        expsessinfo['curr_form_idx'] = form_idx+1

    elif num_repeats and num_visits == num_repeats:
        # If the repeat value is set and we have visited it this number of times, then move on
        expsessinfo['curr_form_idx'] = form_idx+1

    elif goto_form_idx:
        # If a goto form was specified
        expsessinfo['curr_form_idx'] = goto_form_idx
        check_conditional = False

    elif form_idx == exf.count():
        expsessinfo['finished'] = True

        request.session[expsess_key] = expsessinfo
        return HttpResponseRedirect(reverse('terminate_experiment'),args=(experiment_id))
    else:
        expsessinfo['curr_form_idx'] = form_idx+1

    next_formidx = expsessinfo['curr_form_idx']

    # Update our session storage
    request.session[expsess_key] = expsessinfo    

    # Update the next variable for this session
    request.session['next'] = reverse('serve_form', args=(experiment_id, next_formidx,))

    return next_formidx