# Views related to running group sessions

from django.utils import timezone

from django.views.generic.edit import CreateView

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy

from .models import Group, GroupSession, GroupSessionSubjectSession
from .forms import GroupForm, get_group_code_form, GroupSessionForm

from pyensemble.models import Ticket, Session
from pyensemble.tasks import create_tickets

import pdb

class GroupCreateView(LoginRequiredMixin,CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'group/create.html'
    
    def get_success_url(self):
        return reverse_lazy('pyensemble-group:start_groupsession')


def get_session_id(request):
    session_key = request.session['group_session_key']
    session_id = request.session[session_key]['id']
    return session_id

def get_group_session(request):
    return GroupSession.objects.get(pk=get_session_id(request))

@login_required
def start_groupsession(request):

    if request.method == 'POST':
        form = GroupSessionForm(request.POST)

        if form.is_valid():
            # Check whether we need to create a new group
            if form.cleaned_data['group'] == None:
                return HttpResponseRedirect(reverse('pyensemble-group:create_group'))

            # Get our experiment
            experiment = form.cleaned_data['experiment']

            # Get our group
            group = form.cleaned_data['group']

            # Generate a ticket
            expiration_datetime = timezone.now() + timezone.timedelta(minutes=360)
            ticket_list = create_tickets({
                'experiment_id': experiment.id,
                'num_group': 1,
                'group_expiration': expiration_datetime,
            })

            ticket = ticket_list[0]

            # Create a group session
            group_session = GroupSession.objects.create(
                group = group,
                experiment = experiment,
                ticket = ticket,
                )

            # Initialize a group session object in the session cache
            cache_key = group_session.get_cache_key()
            request.session['group_session_key'] = cache_key
            request.session[cache_key] = {'id': group_session.id}

            # Set the state of our group session
            group_session.state = group_session.States.READY
            group_session.save()

            return HttpResponseRedirect(reverse('pyensemble-group:groupsession_status'))

    else:
        form = GroupSessionForm()


    template = 'group/session_start.html'
    context = {
        'form': form
    }

    return render(request, template, context)

@login_required
def end_groupsession(request):
    session = get_group_session(request)

    session.cleanup()

    # Set our session to completed
    session.state = session.States.COMPLETED
    session.save()

    context = {
        'session': session,
    }
    template = 'group/session_status.html'
    return render(request, template, context)

@login_required
def abort_groupsession(request):
    session = get_group_session(request)

    session.state = session.States.ABORTED
    session.save()

    context = {
        'session': session,
    }

    template = 'group/session_status.html'
    return render(request, template, context)

@login_required
def attach_experimenter(request):
    if request.method == 'POST':
        GroupCodeForm = get_group_code_form(code_type='experimenter')
        form = GroupCodeForm(request.POST)

        if form.is_valid():
            # Get the ticket object
            ticket = Ticket.objects.get(experimenter_code=form.cleaned_data['experimenter_code'])

            # Get the session
            session = GroupSession.objects.get(ticket=ticket)
            session.experimenter_attached = True
            session.save()

            # Initialize a session variables cache
            cache_key = ticket.groupsession.get_cache_key()
            request.session['group_session_key'] = cache_key
            request.session[cache_key] = {'id': ticket.groupsession.id}

            return HttpResponseRedirect(reverse('pyensemble-group:groupsession_status'))

    else:
        form = get_group_code_form(code_type='experimenter')

    template = 'group/attach_to_session.html'
    context = {
        'form': form
    }

    return render(request, template, context)

def attach_participant(request):
    if request.method == 'POST':
        GroupCodeForm = get_group_code_form(code_type='participant')
        form = GroupCodeForm(request.POST)

        if form.is_valid():
            # Get the ticket object
            ticket = Ticket.objects.get(participant_code=form.cleaned_data['participant_code'])

            # Cache the group session key in the participant's cache
            cache_key = ticket.groupsession.get_cache_key()
            request.session['group_session_key'] = cache_key
            request.session[cache_key] = {'id': ticket.groupsession.id}

            # Redirect to run_experiment using the full ticket code
            url = '%s?tc=%s'%(reverse('run_experiment', args=[ticket.experiment.id]), ticket.ticket_code)

            return HttpResponseRedirect(url)

    else:
        form = get_group_code_form(code_type='participant')

    template = 'group/attach_to_session.html'
    context = {
        'form': form
    }

    return render(request, template, context)

@login_required
def get_groupsession_participants(request):
    # Get our groupsession ID
    groupsession_id = request.session[request.session['group_session_key']]['id']

    pinfo = GroupSessionSubjectSession.objects.filter(group_session=groupsession_id).values(*['user_session__subject','user_session__subject__name_first','user_session__subject__name_last'])

    # Create a regular dict
    participants = {p['user_session__subject']:{'first': p['user_session__subject__name_first'], 'last': p['user_session__subject__name_last']} for p in pinfo}
    
    return JsonResponse(participants)

@login_required
def groupsession_status(request):
    session = get_group_session(request)

    context = {
        'session': session,
    }

    template = 'group/session_status.html'
    return render(request, template, context)

# Method for setting the states of individual subjects in the group
def set_groupuser_state(request, state):
    # Make sure we have a valid state
    state = state.upper()
    if state not in GroupSessionSubjectSession.States.names:
        raise ValueError(f"{state} not a valid state")

    # Get the group session ID from the session cache
    groupsession_id = get_session_id(request)

    # Get the group session
    group_session = GroupSession.objects.get(pk=groupsession_id)

    # Get the experiment info from the user's session cache
    expsessinfo = request.session[group_session.experiment.get_cache_key()]

    # Get the user session
    user_session = Session.objects.get(pk=expsessinfo['session_id'])

    # Get the conjoint group and user session entry
    gsus = GroupSessionSubjectSession.objects.get(group_session=group_session, user_session=user_session)

    # Set the state
    gsus.state = gsus.States[state]
    gsus.save()
    
    return gsus.state

def is_group_ready(request):
    # Get the group session 
    group_session = get_group_session(request)

    return group_session.group_ready()


def trial_status(request):
    # Get the group session 
    group_session = get_group_session(request)

    data = {'state': group_session.get_context_state()}

    return JsonResponse(data)

@login_required
def start_trial(request):
    group_session = get_group_session(request)

    # Set the context to indicate the trial is running
    group_session.set_context_state('running')

    return HttpResponse(status=200)

@login_required
def end_trial(request):
    # Get the group session
    group_session = get_group_session(request)

    # Set the context to indicate the trial has ended
    group_session.set_context_state('ended')

    # We are now officially waiting for participant responses
    group_session.set_response_pending()

    return HttpResponse(status=200)
