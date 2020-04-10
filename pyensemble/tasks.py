# tasks.py
import datetime, hashlib

from pyensemble.models import Experiment, ExperimentXForm, Subject, Ticket
from pyensemble.forms import TicketCreationForm

from django.urls import reverse
from django.shortcuts import render

from django.http import HttpResponseRedirect

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

    # We have to first create our subject root and then check for existing matches in the database. The reason we have to do it in this order is because of the encryption of the subject table.
    if scheme=='nhdl':
        subject_id_root = '%02d%s%s%02d'%(dob.month, str(last[0]+last[-1:]+first[0]), str(dob.year)[-2:], dob.day)

        # Get a list of all subjects with the same root
        subjects = Subject.objects.filter(subject_id__contains=subject_id_root)

        # Iterate over the existing subjects and see if we have a match
        for currsub in subjects:
            if currsub.name_last.lower() == last and currsub.name_first.lower() == first and currsub.dob == dob:
                return currsub.subject_id, True

        # If we found no match, create a new entry
        subject_id = subject_id_root+str(subjects.count()+1)
        return subject_id, False

    else:
        raise ValueError('unknown subject ID generator')


def create_ticket(request):
    # Creates a ticket for an experiment.
    # Type can be master (multi-use) or user (single-use)
    # pdb.set_trace()

    # Get our request data
    ticket_request = TicketCreationForm(request.POST)

    # Validate the request data
    if ticket_request.is_valid():
        # Get the number of existing tickets
        num_existing_tickets = Ticket.objects.all().count()

        # Initialize our new ticket list
        ticket_list = []

        # Get our experiment
        experiment_id = ticket_request.cleaned_data['experiment_id']
        experiment = Experiment.objects.get(experiment_id=experiment_id)

        # Get our ticket types
        ticket_types = [tt[0] for tt in Ticket.TICKET_TYPE_CHOICES]

        for ticket_type in ticket_types:
            num_tickets = ticket_request.cleaned_data[f'num_{ticket_type}']

            if num_tickets:
                expiration_datetime = ticket_request.cleaned_data[f'{ticket_type}_expiration']

                # Add the ticket(s)
                for iticket in range(num_tickets):
                    num_new_tickets = len(ticket_list)
                    unencrypted_str = '%d_%d'%(num_existing_tickets+num_new_tickets,experiment_id)
                    encrypted_str = hashlib.md5(unencrypted_str.encode('utf-8')).hexdigest()

                    # Add a new ticket to our list
                    ticket_list.append(Ticket(
                        ticket_code=encrypted_str, 
                        experiment=experiment, 
                        type=ticket_type, 
                        expiration_datetime=expiration_datetime)
                    )

        # Create the tickets in the database
        Ticket.objects.bulk_create(ticket_list)

        return HttpResponseRedirect(reverse('experiment_detail', 
        args=(experiment.pk,)))