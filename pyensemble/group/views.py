# Views related to running group sessions

from django.utils import timezone
from django.conf import settings

from django.views.generic.edit import CreateView
from django.views.generic import ListView

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy

from .models import Group, GroupSession, GroupSessionSubjectSession
from .forms import GroupForm, get_group_code_form, GroupSessionForm, GroupSessionNotesForm, GroupSessionFileAttachForm

from pyensemble.models import Ticket, Session
from pyensemble.tasks import create_tickets

import pdb

class GroupCreateView(LoginRequiredMixin,CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'group/create.html'
    
    def get_success_url(self):
        return reverse_lazy('pyensemble-group:start_groupsession')


def attach_subject_to_group(subject, group_id):
    # Get our group
    group = Group.objects.get(pk=group_id)

    # Attach the subject to the group
    group.subjects.add(subject)

    return group


class GroupMemberListView(LoginRequiredMixin, ListView):
    model = Group
    template_name = 'group/membership.html'
    context_object_name = 'subjects'

    def get_queryset(self):
        id = self.kwargs.get('id', None)
        group = Group.objects.get(id=id)

        return group.subjects.all()
    
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        id = self.kwargs.get('id', None)
        group = Group.objects.get(id=id)

        data['group'] = group

        return data

def get_session_id(request):
    session_id = None
    session_key = request.session.get('group_session_key', None)
    if not session_key:
        if settings.DEBUG:
            pdb.set_trace()

    else:
        session_id = request.session[session_key]['id']

    return session_id

def get_group_session(request):
    session_id = get_session_id(request)

    if session_id:
        return GroupSession.objects.get(pk=session_id)

    else:
        return None

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
            cache_key = group_session.cache_key
            request.session['group_session_key'] = cache_key
            request.session[cache_key] = {'id': group_session.id}

            # Set the state of our group session
            group_session.state = group_session.States.READY
            group_session.save()

            request.session.modified = True
            return HttpResponseRedirect(reverse('pyensemble-group:groupsession_status'))

    else:
        form = GroupSessionForm()


    template = 'group/session_start.html'
    context = {
        'form': form
    }

    return render(request, template, context)

@login_required
def terminate_groupsession(request, manner):
    session = get_group_session(request)

    if manner in session.terminal_states:
        session.cleanup()
        session.state = manner
        session.save()

    return HttpResponseRedirect(reverse('pyensemble-group:groupsession_status'))

@login_required
def end_groupsession(request):
    return terminate_groupsession(request, GroupSession.States.COMPLETED)


@login_required
def abort_groupsession(request):
    return terminate_groupsession(request, GroupSession.States.ABORTED)


@login_required
def attach_experimenter(request):
    if request.method == 'POST':
        GroupCodeForm = get_group_code_form(code_type='experimenter')
        form = GroupCodeForm(request.POST)

        if form.is_valid():
            # Get the ticket object
            # See note in attach_participant
            ticket = Ticket.objects.filter(experimenter_code=form.cleaned_data['experimenter_code']).last()

            # Get the session
            session = GroupSession.objects.get(ticket=ticket)
            session.experimenter_attached = True
            session.save()

            # Initialize a session variables cache
            cache_key = ticket.groupsession.cache_key
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
            # NOTE: Their is a small chance of colliding 4-character strings at the start and end of otherwise unique tickets, so always filter and grab the last ticket. This is still error prone without more robust validation, but unlikely for such an error to occur in a low-volume setting.
            ticket = Ticket.objects.filter(participant_code=form.cleaned_data['participant_code']).last()

            # Cache the group session key in the participant's cache
            cache_key = ticket.groupsession.cache_key
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


# @login_required
# def attach_file(request):
#     if request.method == "POST":
#         form = GroupSessionFileAttachForm(request.POST, request.FILES)

#         if form.is_valid():
#             # file is saved
#             form.save()
#             return HttpResponseRedirect(reverse('pyensemble-group:attach_file_success'))
#     else:
#         # Get our group session
#         groupsession_id = request.GET.get('session_id', None)

#         form = GroupSessionFileAttachForm(initial={'groupsession': groupsession_id})

#     context = {
#         'form': form,
#     }

#     return render(request, "group/report/attach_file.html", context)


# def attach_file_success(request):
#     return HttpResponse("Successfully uploaded the file")


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
    if request.method == 'POST':
        form = GroupSessionNotesForm(request.POST)

        if form.is_valid():
            session = GroupSession.objects.get(pk=form.cleaned_data['id'])
            session.notes = form.cleaned_data['notes']
            session.save()
            return HttpResponse("ok")

    else:
        session = get_group_session(request)
        form = GroupSessionNotesForm(instance=session, initial={'id': session.pk})

        context = {
            'session': session,
            'form': form
        }

        template = 'group/session_status.html'
        return render(request, template, context)


def get_groupuser_session(request):
    # Get the group session ID from the session cache
    groupsession_id = get_session_id(request)

    # Get the group session
    group_session = GroupSession.objects.get(pk=groupsession_id)

    # Get the experiment info from the user's session cache
    expsessinfo = request.session[group_session.experiment.cache_key]

    # Get the user session
    user_session = Session.objects.get(pk=expsessinfo['session_id'])

    # Get the conjoint group and user session entry
    gsus = GroupSessionSubjectSession.objects.get(group_session=group_session, user_session=user_session)

    return gsus


# Methods for getting and setting the states of individual subjects in the group
def get_groupuser_state(request):
    # Get our user session
    gsus = get_groupuser_session(request)

    return gsus.States(gsus.state).name


def set_groupuser_state(request, state):
    # Make sure we have a valid state
    state = state.upper()
    if state not in GroupSessionSubjectSession.States.names:
        raise ValueError(f"{state} not a valid state")

    gsus = get_groupuser_session(request)

    # Set the state
    gsus.state = gsus.States[state]
    gsus.save()
    
    return gsus.state


def wait_groupuser_state(request):
    gsus = get_groupuser_session(request)

    if request.method == 'GET':
        target_state = request.GET.getlist('state')

        state = gsus.wait_state(target_state)

        return HttpResponseRedirect(reverse('pyensemble-group:groupuser_state'))


def set_client_ready(request):
    status = set_groupuser_state(request, 'READY_CLIENT')

    return HttpResponse(status)

def init_group_trial():
    group_trial = {
        'timeline': {},
        'feedback': '',
        'stimulus_id': None,
        'presents_stimulus': False,
        'autorun': False,
    }

    return group_trial


@login_required
def start_trial(request):
    group_session = get_group_session(request)

    # Set the context to indicate the trial is running
    group_session.set_context_state('trial:running')

    return HttpResponse(status=200)


@login_required
def end_trial(request):
    # Get the group session
    group_session = get_group_session(request)

    # Set the context to indicate the trial has ended
    group_session.set_context_state('trial:ended')

    # We are now officially waiting for participant responses
    group_session.set_group_response_pending()

    return HttpResponse(status=200)


def trial_status(request):
    # Get the group session 
    group_session = get_group_session(request)

    data = {'state': group_session.get_context_state()}

    return JsonResponse(data)


# Signal that we want to exit the loop we are in
def exit_loop(request):
    get_group_session(request).set_group_exit_loop()

    return HttpResponseRedirect(reverse('pyensemble-group:groupsession_status'))


def groupuser_state(request):
    state = {}
    if request.method == 'GET':
        state = get_groupuser_state(request)

    return JsonResponse(state, safe=False)


def exclude_groupsession(request):
    session_id = request.POST['session']

    session = GroupSession.objects.get(pk=session_id)
    session.exclude = True
    session.save()

    return HttpResponse(f"Marked {session_id} for exclusion")

  
def groupuser_exitloop(request):
    # Get our experiment info
    group_session = get_group_session(request)

    return HttpResponseRedirect(reverse('serve_form', args=(group_session.experiment.id,)))

