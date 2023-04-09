# views.py
import os, re
import json
import hashlib

from django.utils import timezone

from django.core.cache import cache

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView
from django.views.decorators.http import require_http_methods

import django.forms as forms
from django.db import transaction, IntegrityError
from django.db.models import Q

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse, HttpResponseGone

from django.shortcuts import render
from django.urls import reverse, reverse_lazy

from django.conf import settings
from django.views.generic.edit import CreateView, UpdateView, FormView

from pyensemble.models import Ticket, Session, Experiment, Form, Question, ExperimentXForm, FormXQuestion, Stimulus, Subject, Response, DataFormat

from pyensemble.forms import RegisterSubjectForm, TicketCreationForm, ExperimentFormFormset, ExperimentForm, CopyExperimentForm, FormForm, FormQuestionFormset, QuestionCreateForm, QuestionUpdateForm, QuestionPresentForm, QuestionModelFormSet, QuestionModelFormSetHelper, EnumCreateForm, SubjectEmailForm, CaptchaForm

from pyensemble.tasks import fetch_subject_id, get_or_create_prolific_subject, create_tickets

from pyensemble import errors

from pyensemble.utils.parsers import parse_function_spec, fetch_experiment_method
from pyensemble import experiments 

from pyensemble.group.models import GroupSession, GroupSessionSubjectSession
from pyensemble.group.views import get_group_session, set_groupuser_state, init_group_trial

from crispy_forms.layout import Submit

import pdb

def logout_view(request):
    logout(request)

    return HttpResponseRedirect(reverse('home'))

class PyEnsembleHomeView(LoginRequiredMixin,TemplateView):
    template_name = 'pyensemble/pyensemble_home.html'

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

@login_required
def copy_experiment(request, experiment_id):
    template = 'pyensemble/item_copy.html'
    status = 200

    if request.method == 'POST':
        form = CopyExperimentForm(request.POST)

        if form.is_valid():
            # Create a new Experiment
            new_experiment = Experiment.objects.create(title=form.cleaned_data['title'])

            # Now copy all of the ExperimentXForm entries from the parent experiment
            old_exf = ExperimentXForm.objects.filter(experiment__id=experiment_id)

            new_exf = []
            for exf in old_exf:
                exf.pk = None # To prevent overwrite of existing exf entry

                # Replace old experiment object with new experiment object in the exf instance
                exf.experiment = new_experiment 

                # Add the instance to the stack
                new_exf.append(exf)

            # Create all of the new exf entries
            ExperimentXForm.objects.bulk_create(new_exf) 

            return HttpResponseRedirect(reverse('experiment_update', kwargs={'pk': new_experiment.id}))

        else:
            status=400

    else:
        form = CopyExperimentForm()

    context = {
        'form': form,
    }

    return render(request,template,context,status=status)

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

class QuestionCreateView(LoginRequiredMixin,CreateView):
    model = Question
    form_class = QuestionCreateForm
    template_name = 'pyensemble/question_create.html'

    def form_valid(self, form):
        form.instance.data_format = DataFormat.objects.get(id=form.cleaned_data['dfid'])

        # Now save the form
        form.instance.save()

        return super(QuestionCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('question_present', kwargs={'pk': self.object.pk})

class QuestionUpdateView(LoginRequiredMixin,UpdateView):
    model = Question
    form_class = QuestionUpdateForm
    template_name = 'pyensemble/question_update.html'

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
            return HttpResponseRedirect(reverse('editor'))

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
    # Get our experiment object
    experiment = Experiment.objects.get(id=experiment_id)

    # Keep the general session alive
    request.session.set_expiry(settings.SESSION_DURATION)

    # Get cached information for this experiment and session, if we have it
    expsess_key = experiment.cache_key
    expsessinfo = request.session.get(expsess_key,{})

    # Check whether we have a running session, and initialize a new one if not.
    if not expsessinfo.get('running', False): 
        # Pull out our ticket code
        ticket_code = request.GET.get('tc', None)

        # Check whether we have a Prolific subject ID as a parameter
        prolific_pid = request.GET.get('PROLIFIC_PID',None)
        if prolific_pid:
            # Create a subject entry for this participant if necessary
            subject, created = get_or_create_prolific_subject(request)

            # Generate a user ticket and grab its code
            ticket_code = create_tickets({
                'num_user': 1, 
                'experiment_id': experiment_id,
                'subject': subject,
                })[0].ticket_code

        # Process the ticket
        if not ticket_code:
            # Check whether this is a group experiment and fetch the group ticket code if necessary
            if experiment.is_group:
                return HttpResponseRedirect(reverse('attach_participant'))

            return errors.ticket_error(request, None, 'TICKET_MISSING')

        # Get our ticket entry
        try:
            ticket = Ticket.objects.get(ticket_code=ticket_code)

        except:
            return errors.ticket_error(request, ticket_code, 'TICKET_NOT_FOUND')

        # Check to see that the experiment associated with this ticket code matches
        if ticket.experiment.id != experiment_id:
            return errors.ticket_error(request, ticket, 'TICKET_EXPERIMENT_MISMATCH')

        # Make sure ticket hasn't been used
        if ticket.type == 'user' and ticket.used:
            return errors.ticket_error(request, ticket, 'TICKET_ALREADY_USED')

        # Make sure the ticket's validity has commenced
        if ticket.start and timezone.now() < ticket.start:
            return errors.ticket_error(request, ticket, 'TICKET_NOT_YET_VALID')

        # Make sure ticket hasn't expired
        if ticket.expired:
            return errors.ticket_error(request, ticket, 'TICKET_EXPIRED')

        # Handle the situation where we have a pre-assigned subject via the ticket
        subject = subject_id = None

        if ticket.type == 'user' and ticket.subject:
            subject = ticket.subject
            subject_id = subject.subject_id

            # Check whether this is a Prolific subject 
            if subject.id_origin == 'PRLFC':
                prolific_pid = subject_id

            tmp_subject = False

        # If the participant has not yet registered, create a new temporary entry. The id needs to be a unique hash, otherwise we run into collisions.
        if not subject:
            if not request.session.session_key:
                request.session.save()

            subject, created = Subject.objects.get_or_create(subject_id=request.session.session_key)

            tmp_subject = True

        # See whether we were passed in an explicit session_id as a URL parameter
        origin_sessid = request.GET.get('SESSION_ID', None)

        # Initialize a session in the PyEnsemble session table
        session = Session.objects.create(
            experiment = ticket.experiment, 
            ticket = ticket, 
            subject = subject, 
            origin_sessid = origin_sessid
        )

        # Calculate the age of the subject
        if not tmp_subject:
            session.calc_age()
            
        # If this is a group experiment, attach the session to a group session
        if experiment.is_group:
            # Get the group session object associated with this ticket
            group_session = GroupSession.objects.get(ticket=ticket)

            # Add the subject to the group session
            GroupSessionSubjectSession.objects.create(
                group_session = group_session,
                user_session = session,
                )

        # Update our ticket entry
        ticket.used = True
        ticket.save()

        # Get the SONA code if there is one
        sona_code = request.GET.get('sona',None)

        # Deal with the situation in which we are trying to access using a survey code from SONA, but no code has been set
        if 'sona' in request.GET.keys() and not sona_code:
            return render(request,'pyensemble/error.html',{'msg':'No SONA survey code was specified!','next':'/'})

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
            'subject_id': subject_id,
            'prolific_pid': prolific_pid,
            'first_form': True, # will we be serving our first form
            })

    # Set the experiment session info
    request.session[expsess_key] = expsessinfo

    return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

#
# serve_form is the view that handles the running of the experiment following initialization by run_experiment
#
def serve_form(request, experiment_id=None):
    # Initialize our context
    context = {
        'form': None,
        'formset': None,
        'helper': None,
        'form_show_errors': True,
        'captcha': {},
        'timeline': {},
        'timeline_json':'',
        'stimulus': None,
        'skip_trial': False,
        'feedback': '',
        # 'group': {},
    }

    experiment = Experiment.objects.get(pk=experiment_id)

    # Get the key that we can use to retrieve experiment-specific session information for this user   
    expsess_key = experiment.cache_key

    # Make sure the experiment session info is cached in the session info
    # Otherwise restart the experiment
    if expsess_key not in request.session.keys() or not request.session[expsess_key]:
        return render(request,'pyensemble/error.html',{'msg':'Invalid attempt to start or resume the experiment','next':'/'})

    # Get our experiment session info
    expsessinfo = request.session[expsess_key]

    # Update our context with our session ID
    context.update({'session_id': expsessinfo['session_id']})

    # Get the index of the form we're on
    form_idx = expsessinfo['curr_form_idx']

    # Update our first form flag
    context.update({'first_form': expsessinfo['first_form']})

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

    # Add the form to our context
    context.update({
        'form': form,
        'clientside_validation': currform.use_clientside_validation
        })

    # Check to see whether we are dealing with a special form that requires different handling. This is largely to try to maintain backward compatibility with the legacy PHP version of Ensemble
    handler_name = os.path.splitext(currform.form_handler)[0]

    if request.method == 'POST':
        #
        # Process the submitted form
        #

        # Get our PyEnsemble session
        session = Session.objects.get(id=expsessinfo['session_id'])

        # By default we pass captcha test because we don't require it
        passes_captcha = True

        if handler_name == 'form_subject_register':
            formset = RegisterSubjectForm(request.POST)

        elif handler_name == 'form_subject_email':
            formset = SubjectEmailForm(request.POST)

        elif handler_name == 'form_consent':
            captcha_form = CaptchaForm(request.POST)
            passes_captcha = captcha_form.is_valid()
            formset = QuestionModelFormSet(request.POST)

        else:
            formset = QuestionModelFormSet(request.POST)

        # Flag the fact that we've served the first form, irrespective of whether the POST was valid. Write the local timezone for the session to the session object
        if expsessinfo['first_form']:
            session.timezone = request.session.get('timezone', settings.TIME_ZONE)
            session.save()

        expsessinfo.update({'first_form': False})


        # Add the formset to our context
        context.update({'formset': formset})

        # Pull in any miscellaneous info that has been set by the experiment 
        # This can be an arbitrary string, though json-encoded strings are recommended
        misc_info = expsessinfo.get('misc_info', '')

        # Similarly, if we have trial information, get that
        trial_info = expsessinfo.get('trial_info', '')

        if expsessinfo['stimulus_id']:
            stimulus = Stimulus.objects.get(pk=expsessinfo['stimulus_id'])
        else:
            stimulus = None

        # Add the stimulus to our context
        context.update({'stimulus': stimulus})

        if passes_captcha and formset.is_valid():
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

                # Replace the temporary subject with our actual subject in our session instance

                # Get the temporary subject
                tmp_subject = session.subject

                # Attach the registered subject and save the session
                session.subject = subject

                # Calculate the age of our subject
                session.calc_age()

                # Save the updated session
                session.save()

                # Now that we've saved our updated session it is safe to delete the temporary subject
                tmp_subject.delete()

            elif handler_name == 'form_consent':
                question = formset.forms[0]
                response = int(question.cleaned_data.get('option',''))

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

            elif handler_name == 'form_subject_email':
                # Get our subject entry
                subject = Subject.objects.get(subject_id=expsessinfo['subject_id'])

                # Update the email info
                subject.email = formset.cleaned_data['email']

                # Save the subject
                subject.save()

            else:
                # Evaluate any further experiment-form-specific response validation callback. The primary intent is to check for submission of an identical response arising from an inadvertent double form submission.
                if not currform.record_response(request):

                    # If we were told to not record the response, progress on with the experiment without updating the form visit count or getting the next form index
                    return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

                #
                # Save responses to the Response table
                #
                responses = []

                # Increment our response_order variable if we are actually planning to write a response to the database. The same response_order value applies to all questions on this form.
                expsessinfo['response_order']+=1

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

                    # If we are in group session trial, write group session context to trial info for the first response
                    if handler_name in ['group_trial']:
                        if not idx:
                            group_session = get_group_session(request)
                            trial_info = group_session.context.get('params',{})
                        else:
                            trial_info = ""

                    # Create a Response object and append it to our list
                    responses.append(Response(
                        experiment=currform.experiment,
                        subject=Subject.objects.get(subject_id=expsessinfo['subject_id']),
                        session=session,
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
                        trial_info=trial_info,
                        )
                    )

                if responses:
                    Response.objects.bulk_create(responses)

            # Now that the responses have been saved, the user's state, in a group experiment is again unknown
            if handler_name == 'group_trial':
                user_state = set_groupuser_state(request,'UNKNOWN')

            # Update our visit count for this form
            num_visits = expsessinfo['visit_count'].get(form_idx,0)
            num_visits +=1
            expsessinfo['visit_count'][form_idx] = num_visits

            # Determine our next form index
            expsessinfo['curr_form_idx'] = currform.next_form_idx(request)
            request.session.modified=True

            # Move to the next form by calling ourselves
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

        # If the form was not valid and we have to present it again, skip the trial running portion of it, so that we only present the questions
        context.update({'skip_trial':True})

    else:
        #
        # Process the GET request for this form
        #

        # Validate that our subject is still active, i.e. that their session is not expired. 
        session = Session.objects.get(pk=expsessinfo['session_id'])

        if session.expired:
            reset_session(request, experiment_id)

        # Determine whether any conditions on this form have been met
        if not currform.conditions_met(request):
            expsessinfo['curr_form_idx']+=1

            # Go to the next form
            request.session.modified=True
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id,)))

        #
        # Initialize variables that help control the trial preparation logic
        #

        presents_stimulus = False # Does this form present a stimulus. Note that this is not the same as requiring a stimulus for the response(s) to this form to be associated with

        # Determine whether the handler name ends in _s indicating that the form is handling stimuli
        requires_stimulus = True if re.search('_s$',handler_name) else False  

        timeline = {}
        stimulus_id = None

        # Execute a stimulus selection script if one has been specified
        # NOTE: The use of the stimulus_script field transcends stimulus selection: what it accomplishes depends on what the form_handler that is associated with this form in this particular experiment context requires.

        if currform.stimulus_script:
            # Use regexp to get the function name that we're calling
            funcdict = parse_function_spec(currform.stimulus_script)
            funcdict['kwargs'].update({'session_id': expsessinfo['session_id']})

            # Get our selection function
            method = fetch_experiment_method(funcdict['func_name'])

            if handler_name in ['form_feedback','form_end_session']:
                presents_stimulus = False

                # Call the method to generate the feedback content
                feedback = method(request, *funcdict['args'],**funcdict['kwargs'])

                # Add feedback to our context
                context.update({'feedback': feedback})

            elif handler_name in ['group_trial']:
                # Group trials may be of different types. Some may present no stimulus at all whereas others might. Yet other group trials might be controlled by an experimenter (proxy) that controls the trial.

                # Get the group session ID from the session cache
                group_session = get_group_session(request)

                # What group trials have in common is the need for the participants to be synchronized at the start of the trial. Having gotten to this point means that the user is ready for this form to be handled, so indicate that fact.

                user_state = set_groupuser_state(request,'READY_SERVER')

                # Now wait until everyone has reached this point
                group_ready = group_session.wait_group_ready_server()

                if not group_ready:
                    return HttpResponseGone("Group not ready. Try resubmitting the form")

                # Now call the method that will set the parameters for this trial for the whole group. If none is specified, we'll simply serve the next form
                group_trial = init_group_trial()
            
                if method:
                    data = method(request, *funcdict['args'],**funcdict['kwargs'])
                    group_trial.update(data)

                # Add the group trial info to our context
                context.update(group_trial)

                # Unpack other elements of the result
                stimulus_id = group_trial.get('stimulus_id', None)
                presents_stimulus = group_trial.get('presents_stimulus', False)

            else:
                # The default assumption, if selecting a stimulus, is that we will be presenting the stimulus via jsPsych
                presents_stimulus = True

                # Call the select function with the parameters to get the trial timeline specification
                timeline, stimulus_id  = method(request, *funcdict['args'],**funcdict['kwargs'])

        if timeline:
            context.update({
                'timeline': timeline,
                'timeline_json': json.dumps(timeline)
                })

        if stimulus_id:
            expsessinfo['stimulus_id'] = stimulus_id

        #
        # If this form requires a stimulus and there is no stimulus, this means that we have exhausted our stimuli and so we should move on to the next form. 
        # NOTE: Rather than infer this in this way, it would be better to have the state explicitly set in expsessinfo by the method that selects the stimulus and builds the timeline.

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
        if not requires_stimulus:
            expsessinfo['stimulus_id'] = None

        # Get our stimulus and add it to the context
        stimulus_id = expsessinfo.get('stimulus_id', None)
        if stimulus_id:
            context.update({'stimulus': Stimulus.objects.get(id=stimulus_id)})

        #
        # Get our blank form
        #
        if handler_name == 'form_subject_register':
            formset = RegisterSubjectForm(initial={'dob':None})
            
        elif handler_name== 'form_subject_email':
            # Technically, this is not a formset consisting of question forms, but we want to preserve the ability to display a custom form header.
            formset = SubjectEmailForm()

        else:
            formset = QuestionModelFormSet(queryset=form.questions.all().order_by('formxquestion__form_question_num'))

        # Add the formset info to our context
        context.update({'formset': formset})


    if handler_name == 'form_consent':
        context.update({'captcha': {
            'form': CaptchaForm(),
            'site_key': settings.RECAPTCHA_PUBLIC_KEY
            }})

    # Get our formset helper and add the input buttons that we need for this particular form instance
    helper = QuestionModelFormSetHelper()
    # helper.template = 'pyensemble/partly_crispy/question_formset.html'

    # Add our submit button(s)
    if currform.break_loop_button:
        helper.add_input(Submit("submit", currform.break_loop_button_text,css_class='btn-secondary'))

    continue_button_text = getattr(currform, 'continue_button_text', '')
    if not continue_button_text:
        continue_button_text = 'Next'

    helper.add_input(Submit("submit", continue_button_text))

    # Add the helper to our context
    context.update({'helper': helper})

    # Update the last_visited session variable
    expsessinfo['last_visited'] = form_idx

    # If this is the last form we are presenting, take any necessary cleanup actions
    if handler_name == 'form_end_session':
        # Close out our session
        session = Session.objects.get(id=expsessinfo['session_id'])
        session.end_datetime = timezone.now()
        session.save()

        # Check whether we have a SONA redirect to handle
        sona_code = expsessinfo['sona']

        # Remove our cached session info
        request.session.pop(expsess_key, None)

        # Redirect to the SONA site to grant credit if we have a code
        if sona_code:
            context['sona_url'] = Experiment.objects.get(id=experiment_id).sona_url.replace('XXXX',sona_code)

        # Redirect to the Prolific site to grant credit
        if expsessinfo['prolific_pid']:
            # Get the study-specific redirect URL from the experiment table if we have one
            if currform.experiment.params:
                experiment_params = json.loads(currform.experiment.params)

                # Check whether params are specified in a dictionary
                if isinstance(experiment_params,dict):
                    context['prolific_completion_url'] = experiment_params.get('prolific_completion_url', None)
        

    if settings.DEBUG:
        print(context['timeline_json'])

    # Determine our form template (based on the form_handler field)
    template = os.path.join('pyensemble/handlers/', f'{handler_name}.html')

    # Update our context with our session
    context.update({'session': session})

    # Make sure to save any changes to our session cache
    request.session.modified = True
    return render(request, template, context)

@login_required
def create_ticket(request):
    # Creates a ticket for an experiment.
    # Type can be master (multi-use) or user (single-use)

    # Get our request data
    ticket_request = TicketCreationForm(request.POST)

    # Validate the request data
    if ticket_request.is_valid():
        create_tickets(ticket_request.cleaned_data)

        return HttpResponseRedirect(reverse('experiment_update', 
        args=(ticket_request.cleaned_data['experiment_id'],)))

def reset_session(request, experiment_id):
    experiment = Experiment.objects.get(pk=experiment_id)

    expsessinfo = request.session.get(experiment.cache_key)

    if not expsessinfo:
        msg = f'Experiment {experiment_id} session not initialized'
    else:
        request.session.pop(experiment.cache_key, None)
        msg = f'Experiment {experiment_id} session reset'

    return render(request,'pyensemble/message.html',{'msg':msg})

def flush_session_cache(request):
    flush_all = True

    # Make a list of the keys we want to remove
    remove_keys = []
    for key in request.session.keys():
        if flush_all:
            remove_keys.append(key)
        elif key.startswith('exper') or key.startswith('group'):
            remove_keys.append(key)

    num_flushed_keys = 0
    for key in remove_keys:
        if request.session.pop(key, None):
            num_flushed_keys += 1

    request.session.modified=True
    return render(request, 'pyensemble/message.html', {'msg': f"Flushed {num_flushed_keys} session cache entries"})

def record_timezone(request):
    if request.method == 'POST':
        # Extract our timezone
        tzname = request.POST['timezone']

        # Update our Django session cache
        request.session['timezone'] = tzname

        # Update our PyEnsemble subject session
        session_id = request.POST.get('session_id', None)
        if session_id:
            session = Session.objects.get(pk=session_id)
            session.timezone = tzname
            session.save()

        return HttpResponse("ok")
