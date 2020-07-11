# views.py
import os, re
import json
import hashlib
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView
from django.views.decorators.http import require_http_methods

import django.forms as forms
from django.db import transaction, IntegrityError
from django.db.models import Q

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse, reverse_lazy

from django.conf import settings
from django.views.generic.edit import CreateView, UpdateView, FormView

from .models import Ticket, Session, Experiment, Form, Question, ExperimentXForm, FormXQuestion, Stimulus, Subject, Response, DataFormat

from .forms import RegisterSubjectForm, TicketCreationForm, ExperimentFormFormset, ExperimentForm, FormForm, FormQuestionFormset, QuestionCreateForm, QuestionUpdateForm, QuestionPresentForm, QuestionModelFormSet, QuestionModelFormSetHelper, EnumCreateForm

from .tasks import get_expsess_key, fetch_subject_id

from pyensemble.utils.parsers import parse_function_spec, fetch_experiment_method
from pyensemble import experiments 

from crispy_forms.layout import Submit


import pdb

class EditorView(LoginRequiredMixin,TemplateView):
    template_name = 'editor_base.html'

#
# Experiment editing views
#

class ExperimentListView(LoginRequiredMixin,ListView):
    model = Experiment
    context_object_name = 'experiment_list'

class ExperimentCreateView(LoginRequiredMixin,CreateView):
    model = Experiment
    form_class = ExperimentForm
    template_name = 'pyensemble/experiment_update.html'
    
    def get_success_url(self):
        return reverse_lazy('experiment_update', kwargs={'pk': self.object.pk})

class ExperimentUpdateView(LoginRequiredMixin,UpdateView):
    model = Experiment
    template_name = 'pyensemble/experiment_update.html'
    form_class = ExperimentForm

    def get_context_data(self, **kwargs):
        context = super(ExperimentUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ExperimentFormFormset(self.request.POST, instance=self.object)
        else:
            context['formset'] = ExperimentFormFormset(instance=self.object, queryset=self.object.experimentxform_set.order_by('form_order'))

        context['tickets'] = {'master': context['experiment'].ticket_set.filter(Q(type='master', expiration_datetime=None) | Q(type='master',expiration_datetime__gte=timezone.now())),
            'user': context['experiment'].ticket_set.filter(Q(type='user', expiration_datetime=None, used=False) | Q(type='user',expiration_datetime__gte=timezone.now(), used=False))}

        # Get the form for our ticket creation modal
        context['ticket_form'] = TicketCreationForm(initial={'experiment_id':context['experiment'].id})        

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            self.object = form.save()
            if formset.is_valid():
                # Save forms in (new) order
                for idx,f in enumerate(formset.ordered_forms):
                    f.instance.form_order = idx+1
                    f.instance.save()

                # Delete forms flagged for deletion
                for f in formset.deleted_forms:
                    f.instance.delete()

        return super(ExperimentUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('experiment_update', kwargs={'pk': self.object.pk})

def add_experiment_form(request, experiment_id):
    if request.method == 'POST':
        # Get our Experiment instance
        experiment = Experiment.objects.get(id=experiment_id)

        for form_name in json.loads(request.body):
            num_existing = ExperimentXForm.objects.filter(experiment=experiment).count()

            # Get our form instance
            form = Form.objects.get(name=form_name)

            # Create a new entry
            ExperimentXForm.objects.create(experiment_id=experiment_id,form=form,form_order=num_existing+1)

    return HttpResponseRedirect(reverse('experiment_update', kwargs={'pk': experiment_id}))

#
# Form editing views
#

class FormListView(LoginRequiredMixin,ListView):
    model = Form
    context_object_name = 'form_list'

class FormCreateView(LoginRequiredMixin,CreateView):
    model = Form
    form_class = FormForm
    template_name = 'pyensemble/form_create.html'
    
    def get_success_url(self):
        return reverse_lazy('form_update', kwargs={'pk': self.object.pk})

class FormUpdateView(LoginRequiredMixin,UpdateView):
    model = Form
    template_name = 'pyensemble/form_update.html'
    form_class = FormForm

    def get_context_data(self, **kwargs):
        context = super(FormUpdateView, self).get_context_data(**kwargs)

        if self.request.POST:
            context['formset'] = FormQuestionFormset(self.request.POST, instance=self.object)
        else:
            context['formset'] = FormQuestionFormset(instance=self.object, queryset=self.object.formxquestion_set.order_by('form_question_num'))
        
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            self.object = form.save()
            if formset.is_valid():
                # Save forms in (new) order
                for idx,f in enumerate(formset.ordered_forms):
                    f.instance.form_question_num = idx+1
                    f.instance.save()

                # Delete forms flagged for deletion
                for f in formset.deleted_forms:
                    f.instance.delete()

        return super(FormUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('form_update', kwargs={'pk': self.object.pk})

class FormPresentView(LoginRequiredMixin,UpdateView):
    model = Form
    fields=()
    template_name = 'pyensemble/handlers/form_generic.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['form']=context['object']
        context['formset']=QuestionModelFormSet(queryset=context['object'].questions.all().order_by('formxquestion__form_question_num'))

        helper = QuestionModelFormSetHelper()
        helper.template = 'pyensemble/partly_crispy/question_formset.html'

        context['helper'] = helper

        return context


def add_form_question(request, form_id):
    if request.method == 'POST':
        # Get our Experiment instance
        form = Form.objects.get(id=form_id)

        for question_text in json.loads(request.body):
            num_existing = FormXQuestion.objects.filter(form=form).count()

            # Get our form instance
            question = Question.objects.get(text=question_text)

            # Create a new entry
            FormXQuestion.objects.create(form=form,question=question,form_question_num=num_existing+1)

    return HttpResponseRedirect(reverse('form_update', kwargs={'pk': form_id}))

#
# Question editing views
#

class QuestionListView(LoginRequiredMixin,ListView):
    model = Question
    context_object_name = 'question_list'

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)

    #     return context

class QuestionCreateView(LoginRequiredMixin,CreateView):
    model = Question
    form_class = QuestionCreateForm
    template_name = 'pyensemble/question_create.html'

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)

    #     return context

    def form_valid(self, form):
        context = self.get_context_data()

        form.instance.data_format = DataFormat.objects.get(id=form.cleaned_data['dfid'])

        # Need to create the unique hash
        form.instance.unique_hash

        # Now save the form
        form.instance.save()

        return super(QuestionCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('question_present', kwargs={'pk': self.object.pk})

class QuestionUpdateView(LoginRequiredMixin,UpdateView):
    model = Question
    form_class = QuestionUpdateForm
    template_name = 'pyensemble/question_create.html'
    # context_object_name = 'question'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'].helper.form_action = reverse('question_update', kwargs={'pk': self.object.pk})

        return context

    def form_valid(self, form):
        context = self.get_context_data()

        form.instance.data_format = DataFormat.objects.get(id=form.cleaned_data['dfid'])
        form.instance.save()
        return super(QuestionUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('question_present', kwargs={'pk': self.object.pk})

class QuestionPresentView(LoginRequiredMixin,UpdateView):
    model = Question
    form_class = QuestionPresentForm
    template_name = 'pyensemble/question_present.html'

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)

    #     return context

#
# Views for enumerated response options
# 
class EnumListView(LoginRequiredMixin,ListView):
    model = DataFormat
    context_object_name = 'enum_list'
    template_name = 'pyensemble/enum_list.html'
    ordering = ['pk']

class EnumCreateView(LoginRequiredMixin,CreateView):
    model = DataFormat
    form_class = EnumCreateForm
    template_name = 'pyensemble/enum_create.html'

    def form_valid(self,form):
        try:
            form.save()
            return HttpResponse("Created the enum")

        except:
            return HttpResponseBadRequest('The enum already exists')

    def get_success_url(self):
        return reverse_lazy('editor')
#
# Views for running experiments
#

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
        ticket = request.GET.get('tc',None)

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
        if ticket.experiment.id != experiment_id:
            return HttpResponseBadRequest('This ticket is not valid for this experiment')

        # Make sure ticket hasn't been used or expired
        if ticket.expired:
            return HttpResponseBadRequest('The ticket has expired')

        # Get the SONA code if there is one
        sona_code = request.GET.get('sona',None)

        # Deal with the situation in which we are trying to access using a survey code from SONA, but no code has been set
        if 'sona' in request.GET.keys() and not sona_code:
            return render(request,'pyensemble/error.html',{'msg':'No SONA survey code was specified!','next':'/'})

        # Initialize a session in the PyEnsemble session table
        session = Session.objects.create(experiment=ticket.experiment, ticket=ticket)

        # Update our ticket entry
        ticket.used = True
        ticket.save()

        # Update our Django session information
        expsessinfo.update({
            'session_id': session.id,
            'curr_form_idx': 0,
            'response_order': 0,
            'stimulus_id': None,
            'break_loop': False,
            'last_in_loop': {},
            'visit_count': {},
            'running': True,
            'sona': sona_code,
            })

    # Set the experiment session info
    request.session[expsess_key] = expsessinfo

    return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

#
# serve_form is the view that handles the running of the experiment following initialization by run_experiment
#
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
    form = Form.objects.get(id=currform.form.id)

    # Clean the header and footer, replacing backslashes
    form.header = form.header.replace('\\','')
    form.footer = form.footer.replace('\\','')

    # Check to see whether we are dealing with a special form that requires different handling. This is largely to try to maintain backward compatibility with the legacy PHP version of Ensemble
    handler_name = os.path.splitext(currform.form_handler)[0]

    # Initialize other context
    trialspec = {}
    timeline = []
    stimulus = None

    if request.method == 'POST':
        #
        # Process the submitted form
        #
        if handler_name == 'form_subject_register':
            formset = RegisterSubjectForm(request.POST)
        else:
            # form = Form.objects.get(form_id=currform.form_id)
            formset = QuestionModelFormSet(request.POST)

        # Pull in any miscellaneous info that has been set by the experiment 
        # This can be an arbitrary string, though json-encoded strings are recommended
        misc_info = expsessinfo.get('misc_info','')

        if expsessinfo['stimulus_id']:
            stimulus = Stimulus.objects.get(pk=expsessinfo['stimulus_id'])
        else:
            stimulus = None


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

            elif handler_name == 'form_consent':
                question = formset.forms[0]
                response = int(question.cleaned_data.get('option',''))

                # pdb.set_trace()
                choices = question.instance.choices()
                if choices[response][1].lower() != 'agree':
                    return render(request,'pyensemble/message.html',{
                        'msg': 'You must agree to provided informed consent if you wish to continue with this experiment!<br> Please click <a href="%s">here</a> if you disagreed in error.<br> Thank you for considering taking part in this experiment.'%(reverse('serve_form',args=(experiment_id,))),
                        'add_home_url':False,
                        })

                # Update our visit count
                num_visits = expsessinfo['visit_count'].get(form_idx,0)
                num_visits +=1
                expsessinfo['visit_count'][form_idx] = num_visits

                # Determine our next form index
                expsessinfo['curr_form_idx'] = currform.next_form_idx(request)
                request.session.modified=True

                # Move to the next form by calling ourselves
                return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

            else:
                #
                # Save responses to the Response table
                #
                responses = []

                if form.name == 'ftap_expo_practice_trial':
                    pdb.set_trace()

                """
                originally, we made the if statement below to log jsp data for forms without questions
                ended up having to add a question (make it so it doesn't show), so now this catch isn't
                needed
                
                # Check below to see if we presented a stim and collected only jspsych responses (no pyensemble question)
                if not formset.forms and request.POST.get('jspsych_data',''):
                    responses.append(Response(
                                experiment=currform.experiment,
                                subject=Subject.objects.get(subject_id=expsessinfo['subject_id']),
                                session=Session.objects.get(id=expsessinfo['session_id']),
                                form=currform.form,
                                form_order=form_idx,
                                stimulus=stimulus,
                                #form_question_num=0,
                                question_id=0,
                                question_iteration=0, # this needs to be modified to reflect original Ensemble intent
                                response_order=0,
                                jspsych_data=request.POST.get('jspsych_data',''),
                                misc_info=misc_info,
                                )
                            )
                
                else:
                    """
                for idx,question in enumerate(formset.forms):
            
                    # Pre-process certain fields
                    response = question.cleaned_data.get('option','')

                    if question.instance.data_format.df_type == 'enum':
                        if question.instance.html_field_type=='checkbox':
                            # This is a HACK and needs to be fixed
                            # checkbox should be enum
                            # enums need to be stored in power of two format (like Ensemble), so that we can have multiple checkbox responses selected
                            response_text = ','.join(response)
                            response_enum = None
                        else:
                            response_enum = int(response)
                            response_text = ''
                    else:
                        response_text = response
                        response_enum = None

                    declined=question.cleaned_data.get('decline',False)


                    # Get jsPsych data if we have it, but only write it for the first question
                    if not idx:
                        jspsych_data = request.POST.get('jspsych_data','')
                    else:
                        jspsych_data = ''

                    responses.append(Response(
                        experiment=currform.experiment,
                        subject=Subject.objects.get(subject_id=expsessinfo['subject_id']),
                        session=Session.objects.get(id=expsessinfo['session_id']),
                        form=currform.form,
                        form_order=form_idx,
                        stimulus=stimulus,
                        question=question.instance,
                        form_question_num=idx,
                        question_iteration=1, # this needs to be modified to reflect original Ensemble intent
                        response_order=expsessinfo['response_order'],
                        response_text=response_text,
                        response_enum=response_enum,
                        jspsych_data=jspsych_data,
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
        presents_stimulus = False # Does this form present a stimulus. Note that this is not the same as requiring a stimulus for the response(s) to this form to be associated with

        # Determine whether the handler name ends in _s indicating that the form is handling stimuli
        requires_stimulus = True if re.search('_s$',handler_name) else False  

        # Determine whether any conditions on this form have been met
        if not currform.conditions_met(request):
            expsessinfo['curr_form_idx']+=1

            # Go to the next form
            request.session.modified=True
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

        # Execute a stimulus selection script if one has been specified
        if currform.stimulus_script:
            presents_stimulus = True

            # Use regexp to get the function name that we're calling
            funcdict = parse_function_spec(currform.stimulus_script)
            funcdict['kwargs'].update({'session_id': expsessinfo['session_id']})

            # Get our selection function
            method = fetch_experiment_method(funcdict['func_name'])

            # Call the select function with the parameters to get the trial timeline specification
            timeline, stimulus_id  = method(request, *funcdict['args'],**funcdict['kwargs'])

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

            # Go to that next form
            request.session.modified=True
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

        #
        # Reset our session stimulus_id variable if appropriate
        #
        stimulus = None
        if not requires_stimulus:
            expsessinfo['stimulus_id'] = None
        else:
            stimulus_id = expsessinfo.get('stimulus_id',None)
            if stimulus_id:
                stimulus = Stimulus.objects.get(id=stimulus_id)

        #
        # Get our blank form
        #
        if handler_name == 'form_subject_register':
            form = RegisterSubjectForm()
            formset = None
        else:
            formset = QuestionModelFormSet(queryset=form.questions.all().order_by('formxquestion__form_question_num'))

    # Determine any other trial control parameters that are part of the JavaScript injection
    trialspec.update({
        'questions_after_media_finished': True,
        'skip': skip_trial,
        })

    # Get our formset helper. The following helper information should ostensibly stored with the form definition, but that wasn't working
    helper = QuestionModelFormSetHelper()
    helper.template = 'pyensemble/partly_crispy/question_formset.html'

    helper.add_input(Submit("submit", "Next"))

    # Create our context to pass to the template
    context = {
        'form': form,
        'formset': formset,
        'form_show_errors': True,
        'helper': helper,
        'timeline': timeline,
        'timeline_json': json.dumps(timeline),
        'trialspec': trialspec,
        'stimulus': stimulus,
       }

    if settings.DEBUG:
        print(context['timeline_json'])

    # Determine our form template (based on the form_handler field)
    form_template = os.path.join('pyensemble/handlers/', f'{handler_name}.html')

    # Update the last_visited session variable
    expsessinfo['last_visited'] = form_idx

    if handler_name == 'form_end_session':
        # Close out our session
        session = Session.objects.get(id=expsessinfo['session_id'])
        session.end_datetime = timezone.now()
        session.save()

        # Check whether we have a SONA redirect to handle
        sona_code = expsessinfo['sona']

        # Remove our cached session info
        request.session.pop(expsess_key,None)

        # Redirect to the SONA site to grant credit if we have a code
        if sona_code:
            context['sona_url'] = Experiment.objects.get(id=experiment_id).sona_url.replace('XXXX',sona_code)

    # Make sure to save any changes to our session cache
    request.session.modified=True
    return render(request, form_template, context)

@login_required
def create_ticket(request):
    # Creates a ticket for an experiment.
    # Type can be master (multi-use) or user (single-use)

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
        experiment = Experiment.objects.get(id=experiment_id)

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

        return HttpResponseRedirect(reverse('experiment_update', 
        args=(experiment.pk,)))

def reset_session(request, experiment_id):
    expsess_key = get_expsess_key(experiment_id)
    expsessinfo = request.session.get(expsess_key)

    if not expsessinfo:
        msg = f'Experiment {experiment_id} session not initialized'
    else:
        msg = f'Experiment {experiment_id} session reset'
        request.session[expsess_key] = {}

    return render(request,'pyensemble/message.html',{'msg':msg})
