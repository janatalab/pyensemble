# tasks.py

from pyensemble.models import Experiment, ExperimentXForm

import pdb

def run_experiment(experiment_id=None):
    # Get the experiment by its id
    if experiment_id:
        experiment = Experiment.objects.get(experiment_id=experiment_id)
    else:
        return

    # Check for existence of the response table

    # User the experiment_x_form entries to run the experiment
    exf = ExperimentXForm.objects.filter(experiment_id=experiment_id).order_by('form_order')
    num_forms = len(exf)

    #
    # Iterate over the forms, but in a way that deals with looping
    #

    # initialize a dictionary to keep track of iteratons by   form_order_idx
    num_iter = [0]*num_forms

    currform_idx = 1 # initialize the form order index to the start
    while currform_idx <= num_forms:
        entry = exf.get(form_order=currform_idx)

        num_iter[currform_idx-1] += 1

        print('%d, %d, %s, %s'%(currform_idx, num_iter[currform_idx-1], entry.form.form_name, entry.form_handler))

        # Generate our view of this form
        present_form()


        # Determine what the next form is
        if entry.goto and num_iter[currform_idx-1]<entry.repeat:
            currform_idx = entry.goto
        else:
            currform_idx += 1


