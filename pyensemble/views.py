# views.py
import os, re
import json
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

from .models import Ticket, Session, Experiment, Form, Question, ExperimentXForm, Stimulus, Subject, Response
from .forms import QuestionModelForm, RegisterSubjectForm, QuestionModelFormSetHelper, TicketCreationForm

from .tasks import get_expsess_key, fetch_subject_id
from pyensemble.utils.parsers import parse_function_spec
from pyensemble import selectors 

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

        # Get the form for our ticket creation modal
        context['ticket_form'] = TicketCreationForm(initial={'experiment_id':context['experiment'].experiment_id})

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context


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

    # Check whether we have a running session, and initialize a new one if not.
    if not expsessinfo.get('running',False): 
        ticket = request.GET['tc']

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
        session = Session.objects.create(experiment=ticket.experiment, ticket=ticket)

        # Update our ticket entry
        ticket.used = True
        ticket.save()

        # Update our Django session information
        expsessinfo.update({
            'session_id': session.session_id,
            'curr_form_idx': 0,
            'response_order': 0,
            'stimulus_id': None,
            'break_loop': False,
            'last_in_loop': {},
            'visit_count': {},
            'running': True})

    # Set the experiment session info
    request.session[expsess_key] = expsessinfo

    return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

def serve_form(request, experiment_id=None):
    # Get the key that we can use to retrieve experiment-specific session information for this user   
    expsess_key = get_expsess_key(experiment_id)

    # Make sure the experiment session info is cached in the session info
    # Otherwise restart the experiment
    if expsess_key not in request.session.keys() or not request.session[expsess_key]:
        return render(request,'pyensemble/error.html',{'msg':'Invalid attempt to start or resume the experiment','next':'/'})

    # Get our experiment session info
    expsessinfo = request.session[expsess_key]

    # Get the index of the form we're on
    form_idx = expsessinfo['curr_form_idx']

    #
    # Get our form stack and extract our current form
    #
    exf = ExperimentXForm.objects.filter(experiment=experiment_id).order_by('form_order')
    currform = exf[form_idx]

    # Get the form instance
    form = Form.objects.get(form_id=currform.form_id)

    # Clean the header, replacing backslashes
    form.header = form.header.replace('\\','')
    form.footer = form.footer.replace('\\','')

    # Return error if we are dealing with a multi-question question. Need to add handling for these at a later date
    if form.questions.filter(heading_format='multi-question'):
        expsessinfo['curr_form_idx'] = currform.next_form_idx(request)
        request.session.modified=True                
        return HttpResponseRedirect(reverse('feature_not_enabled',args=('multi-question',)))

    # Check to see whether we are dealing with a special form that requires different handling. This is largely to try to maintain backward compatibility with the legacy PHP version of Ensemble
    form_handler = currform.form_handler
    handler_name = os.path.splitext(form_handler)[0]

    if handler_name == 'form_start_session':
        # We've already done the initialization, so set our index to the next form
        expsessinfo['curr_form_idx'] += 1
        request.session.modified = True
        return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

    # Define our formset
    QuestionModelFormSet = forms.modelformset_factory(Question, form=QuestionModelForm, extra=0, max_num=1)

    # Get our formset helper. The following helper information should ostensibly stored with the form definition, but that wasn't working
    helper = QuestionModelFormSetHelper()
    helper.add_input(Submit("submit", "Next"))
    helper.template = 'pyensemble/crispy_overrides/table_inline_formset.html'

    # Initialize other context
    trialspec = {}
    timeline = []

    if request.method == 'POST':
        #
        # Process the submitted form
        #
        if handler_name == 'form_subject_register':
            formset = RegisterSubjectForm(request.POST)
        else:
            # form = Form.objects.get(form_id=currform.form_id)
            formset = QuestionModelFormSet(request.POST)

        if formset.is_valid():
            expsessinfo['response_order']+=1

            #
            # Write data to the database. With only a couple of exceptions, based on form_handler, this will be to the Response table
            #
            if handler_name == 'form_subject_register':
                # Generate our subject ID
                subject_id, exists = fetch_subject_id(formset.cleaned_data, scheme='nhdl')

                # Get or create our subject entry (might already exist from previous session)
                if exists:
                    subject = Subject.objects.get(subject_id=subject_id)
                else:
                    subject = Subject.objects.create(
                        subject_id = subject_id,
                        name_first = formset.cleaned_data['name_first'],
                        name_last = formset.cleaned_data['name_last'],
                        dob = formset.cleaned_data['dob'],
                    )

                # Update the demographic info
                subject.sex = formset.cleaned_data['sex']
                subject.race = formset.cleaned_data['race']
                subject.ethnicity = formset.cleaned_data['ethnicity']

                # Save the subject
                subject.save()
                expsessinfo['subject_id'] = subject_id

                # Update the session table
                session = Session.objects.get(pk=expsessinfo['session_id'])
                session.subject = subject
                session.save()

            else:
                #
                # Save responses to the Response table
                #
                responses = []
                for idx,question in enumerate(formset.forms):
                    # Pre-process certain fields
                    response_enum= question.cleaned_data.get('option','')
                    if response_enum:
                        response_enum = int(response_enum)
                    else:
                        response_enum = None

                    response_text=question.cleaned_data.get('response_text','')
                    declined=question.cleaned_data.get('decline',False)
                    misc_info='' # json string with jsPsych data
                    if expsessinfo['stimulus_id']:
                        stimulus = Stimulus.objects.get(pk=expsessinfo['stimulus_id'])
                    else:
                        stimulus = None

                    responses.append(Response(
                        experiment=currform.experiment,
                        subject=Subject.objects.get(subject_id=expsessinfo['subject_id']),
                        session=Session.objects.get(session_id=expsessinfo['session_id']),
                        form=currform.form,
                        form_order=form_idx,
                        stimulus=stimulus,
                        qdf=question.cleaned_data['question_id'].questionxdataformat_set.all()[0],
                        form_question_num=idx,
                        question_iteration=1, # this needs to be modified to reflect original Ensemble intent
                        response_order=expsessinfo['response_order'],
                        response_text=response_text,
                        response_enum=response_enum,
                        decline=declined,
                        misc_info=misc_info,
                        )
                    )

                if responses:
                    Response.objects.bulk_create(responses)

            # Update our visit count
            num_visits = expsessinfo['visit_count'].get(form_idx,0)
            num_visits +=1
            expsessinfo['visit_count'][form_idx] = num_visits

            # Get and set the break_loop state
            # expsessinfo['break_loop'] = formset.cleaned_data.get('break_loop',True)

            # Determine our next form index
            expsessinfo['curr_form_idx'] = currform.next_form_idx(request)
            request.session.modified=True

            # Move to the next form by calling ourselves
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))
            
        # If the form was not valid and we have to present it again, skip the trial running portion of it, so that we only present the questions
        skip_trial = True

    else:
        #
        # Process the GET request for this form
        #

        # Initialize variables
        skip_trial = False
        conditions_met = True # Assume all conditions have been met
        presents_stimulus = False # Does this form present a stimulus

        # Determine whether the handler name ends in _s indicating that the form is handling stimuli
        requires_stimulus = True if re.search('_s$',handler_name) else False  
        # Determine whether any conditions on this form have been met
        conditions_met = currform.conditions_met(request)

        # Execute a stimulus selection script if one has been specified
        if currform.stimulus_matlab:
            presents_stimulus = True

            # Use regexp to get the function name that we're calling
            funcdict = parse_function_spec(currform.stimulus_matlab)

            # Check whether we specified by a module and a method
            parsed_funcname = funcdict['func_name'].split('.')
            module = parsed_funcname[0]

            if len(parsed_funcname)==1:
                method = 'select'
            elif len(parsed_funcname)==2:
                method = parsed_funcname[1]
            else:
                raise ValueError('Method-nesting too deep')

            # Get the module handle from pyensemble.selectors
            select_module = getattr(selectors,module)

            # Get the method handle
            select_func = getattr(select_module,method)

            # Call the select function with the parameters to get the trial specification
            timeline, stimulus_id  = select_func(request, *funcdict['args'],**funcdict['kwargs'])

            expsessinfo['stimulus_id'] = stimulus_id
        else:
            timeline = {}

        #
        # If this form requires a stimulus and there is no stimulus, this means that we have exhausted our stimuli and so we should move on to the next form
        #
        if presents_stimulus and not timeline:
            # If we are at the start of a loop, then any forms within the loop should not be presented, so skip to the form after the end of the loop
            if form_idx in expsessinfo['last_in_loop'].keys():
                expsessinfo['curr_form_idx']=expsessinfo['last_in_loop'][form_idx]+1
            else:
                expsessinfo['curr_form_idx']+=1

            pdb.set_trace()

            # Go to that next form
            request.session.modified=True
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

        #
        # Reset our session stimulus_id variable if appropriate
        #
        if not requires_stimulus:
            expsessinfo['stimulus_id'] = None

        #
        # Get our blank form
        #
        if handler_name == 'form_subject_register':
            form = RegisterSubjectForm()
            formset = None
        else:
            formset = QuestionModelFormSet(queryset=form.questions.all())

    # Determine any other trial control parameters that are part of the JavaScript injection
    trialspec.update({
        'questions_after_media_finished': True,
        'skip': skip_trial,
        })

    # Create our context to pass to the template
    context = {
        'form': form,
        'formset': formset,
        'exf': currform,
        'helper': helper,
        'timeline': timeline,
        'timeline_json': json.dumps(timeline),
        'trialspec': trialspec,
       }

    # Determine our form template (based on the form_handler field)
    form_template = os.path.join('pyensemble/handlers/', f'{handler_name}.html')

    # Update the last_visited session variable
    expsessinfo['last_visited'] = form_idx

    if handler_name == 'form_end_session':
        # Close out our session
        session = Session.objects.get(session_id=expsessinfo['session_id'])
        session.end_datetime = timezone.now()
        session.save()

        # Remove our cached session info
        request.session.pop(expsess_key,None)

    # Make sure to save any changes to our session cache
    request.session.modified=True
    return render(request, form_template, context)

