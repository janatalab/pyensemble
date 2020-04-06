# views.py
import os
from django.utils import timezone

from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView
from django.views.decorators.http import require_http_methods

import django.forms as forms
from django.db.models import Q

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse

from django.conf import settings

from .models import Ticket, Session, Experiment, Form, Question, ExperimentXForm
from .forms import QuestionModelForm, RegisterSubjectForm, QuestionModelFormSetHelper

from .tasks import get_expsess_key, fetch_subject_id

from crispy_forms.layout import Submit

import pdb

# @login_required
class EditorView(TemplateView):
    template_name = 'editor_base.html'

class ExperimentListView(ListView):
    model = Experiment
    context_object_name = 'experiment_list'

class ExperimentDetailView(DetailView):
    model = Experiment
    context_object_name = 'experiment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Arrange our form data
        context['forms'] = context['experiment'].experimentxform_set.all().order_by('form_order')

        # Get our master and user tickets
        context['tickets'] = {'master': context['experiment'].ticket_set.filter(Q(type='master', expiration_datetime=None) | Q(type='master',expiration_datetime__gte=timezone.now())),
            'user': context['experiment'].ticket_set.filter(Q(type='user', expiration_datetime=None) | Q(type='user',expiration_datetime__gte=timezone.now()))}

        return context

class FormListView(ListView):
    model = Form
    context_object_name = 'form_list'

class FormDetailView(DetailView):
    model = Form
    context_object_name = 'form'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Arrange our form data
        context['questions'] = context['form'].formxquestion_set.all().order_by('form_question_num')

        return context

class QuestionListView(ListView):
    model = Question
    context_object_name = 'question_list'

class QuestionDetailView(DetailView):
    model = Question
    context_object_name = 'question'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

# Start experiment
@require_http_methods(['GET'])
def run_experiment(request, experiment_id=None):
    # Keep the general session alive
    request.session.set_expiry(settings.SESSION_DURATION)

    # Get cached information for this experiment and session, if we have it
    expsess_key = get_expsess_key(experiment_id)
    expsessinfo = request.session.get(expsess_key,{})

    # pdb.set_trace()

    # Check whether we have a running session, and initialize a new one if not.
    if not expsessinfo.get('running',False): 
        ticket = request.GET['ticket']

        # Process the ticket
        if not ticket:
            return HttpResponseBadRequest('A ticket is required to start the experiment')

        # Get our ticket entry
        ticket = Ticket.objects.filter(ticket_code=ticket)

        if not ticket.exists():
            return HttpResponseBadRequest('A matching ticket was not found')
        else:
            ticket = ticket[0]

        # Check to see that the experiment associated with this ticket code matches
        if ticket.experiment.experiment_id != experiment_id:
            return HttpResponseBadRequest('This ticket is not valid for this experiment')

        # Make sure ticket hasn't been used or expired
        if ticket.expired:
            return HttpResponseBadRequest('The ticket has expired')

        # Initialize a session in the PyEnsemble session table
        session = Session.objects.create(experiment=experiment_id, ticket=ticket)

        # Update our ticket entry
        ticket.used = True
        ticket.save()

        # Update our Django session information
        expsessinfo.update({
            'session_id': session.session_id,
            'curr_form_idx': 0,
            'visit_count': {},
            'running': True})

    # Set the experiment session info
    request.session[expsess_key] = expsessinfo

    return HttpResponseRedirect(reverse('serve_form', 
        args=(experiment_id, expsessinfo['curr_form_idx'],)))

def serve_form(request, experiment_id=None, form_idx=None):
    # Make sure we are dealing with an active session
    expsess_key = get_expsess_key(experiment_id)

    if expsess_key not in request.session.keys():
        return HttpResponseBadRequest()

    # Get our experiment session info
    expsessinfo = request.session.get(expsess_key)

    # Get our form stack
    exf = ExperimentXForm.objects.filter(experiment=experiment_id).order_by('form_order')

    currform = exf[form_idx]

    # Check to see whether we are dealing with a special form that requires different handling. This is largely to try to maintain backward compatibility with the legacy PHP version of Ensemble
    form_handler = currform.form_handler
    handler_name = os.path.splitext(form_handler)[0]

    if handler_name == 'form_start_session':
        # We've already done the initialization, so move on to the next form
        expsessinfo['curr_form_idx'] = form_idx+1

        # Update our session storage
        request.session[expsess_key] = expsessinfo

        return HttpResponseRedirect(reverse('serve_form', args=(experiment_id, expsessinfo['curr_form_idx'],)))

    # Define our formset
    QuestionModelFormSet = forms.modelformset_factory(Question, form=QuestionModelForm, extra=0, max_num=1)

    # Get our formset helper
    helper = QuestionModelFormSetHelper()
    helper.add_input(Submit("submit", "Submit"))
    helper.template = 'pyensemble/crispy_overrides/table_inline_formset.html'


    if request.method == 'POST':
        if handler_name == 'form_subject_register':
            formset = RegisterSubjectForm(request.POST)
        else:
            form = Form.objects.get(form_id=currform.form_id)
            formset = QuestionModelFormSet(request.POST)

        # pdb.set_trace()

        if formset.is_valid():
            #
            # Write data to the database. With only a couple of exceptions, based on form_handler, this will be to the Response table
            #
            if handler_name == 'form_subject_register':
                # Generate our subject ID
                subject_id, exists = fetch_subject_id(formset.cleaned_data, scheme='nhdl')

                pdb.set_trace()

                # Get or create our subject entry (might already exist from previous session)
                if exists:
                    subject = Subject.objects.get(subject_id=subject_id)
                else:
                    subject,created = Subject.objects.create(
                        subject_id = subject_id,
                        name_first = formset.cleaned_data['name_first'],
                        name_last = formset.cleaned_data['name_last'],
                        dob = formset.cleaned_data['dob'],
                    )

                # Update this info if not set
                if not subject.sex:
                    subject.sex = formset.cleaned_data['sex']

                if not subject.race:
                    subject.race = formset.cleaned_data['race']

                if not subject.ethnicity:
                    subject.ethnicity = formset.cleaned_data['ethnicity']

                # Save the subject
                subject.save()

                expsessinfo['subject_id'] = subject_id

            else:
                pass



            # Update our visit count
            num_visits = expsessinfo['visit_count'].get(form_idx,0)
            num_visits +=1
            expsessinfo['visit_count'][form_idx] = num_visits

            # Update our session storage
            request.session[expsess_key] = expsessinfo

            #
            # Determine where we are going next
            #
            next_formidx = currform.determine_next_form(request)

            # Move to the next form by calling ourselves
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id, next_formidx,)))
            
        # If the form was not valid and we have to present it again, skip the trial running portion of it, so that we only present the questions
        # pdb.set_trace()
        skip_trial = True

    else:
        skip_trial = False
        # Check the conditonal specification on the form we intend to go to, in order to make sure we can go there
        if currform.condition:
            # Parse the condition specification and evaluate it
            # This remains to be implemented 
            currform.determine_next_form(request)
            return HttpResponseRedirect(reverse('feature_not_enabled',args=('form conditionals',)))

        # Get our blank form
        if handler_name == 'form_subject_register':
            form = RegisterSubjectForm()
            formset = None
        else:
            form = Form.objects.get(form_id=currform.form_id)

            # Return error if we are dealing with a multi-question question. Need to add handling for these at a later date
            if form.questions.filter(heading_format='multi-question'):
                currform.determine_next_form(request)
                return HttpResponseRedirect(reverse('feature_not_enabled',args=('multi-question',)))

            formset = QuestionModelFormSet(queryset=form.questions.all())

        # Execute a stimulus selection script if one has been specified
        if currform.stimulus_matlab:
            # Use regexp to get the function name that we're calling
            funcname = '^{}('
            params = '({})'

            # Get the function handle from pyensemble.selectors
            select_func = pyensemble.selectors.attr(funcname)

            # Call the select function with the parameters
            stimulus_id = select_func(params)
        else:
            stimulus_id = None

        # Check whether handler_name ends in _s. If it does not, set the current stimulus value to None

        expsessinfo['stimulus_id'] = stimulus_id

    # Create our context
    context = {
        'form': form,
        'formset': formset,
        'exf': currform,
        'helper': helper,
        'stimulus': Stimulus.objects.get(pk=stimulus_id),
       }

    #
    # Additional context variables (these should maybe be part of the form creation, e.g. setting of stimulus_id as a hidden value)
    #

    # Determine what media, if any, we are presenting
    # media = {}

    # Determine any other trial control parameters that are part of the JavaScript injection
    context['trial'] = {
        'questions_after_media_finished': True,
        'skip': skip_trial,
        }

    # Determine our form template (based on the form_handler field)
    form_template = os.path.join('pyensemble/handlers/', f'{handler_name}.html')

    # Update the last_visited session variable
    expsessinfo['last_visited'] = form_idx

    # Update our session storage
    request.session[expsess_key] = expsessinfo

    # pdb.set_trace()
    return render(request, form_template, context)

