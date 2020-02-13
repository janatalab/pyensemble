# views.py
import os

from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView
from django.views.decorators.http import require_http_methods

import django.forms as forms

from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse

from django.conf import settings

from .models import Experiment, Form, Question, ExperimentXForm
from .forms import QuestionModelForm, RegisterSubjectForm

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

def get_expsess_key(experiment_id):
    return f'experiment_{experiment_id}'

# Start experiment
@require_http_methods(['GET'])
def run_experiment(request, experiment_id=None, ticket=None):
    # Keep the general session alive
    request.session.set_expiry(settings.SESSION_DURATION)

    # Get cached information for this experiment and session, if we have it
    expsess_key = get_expsess_key(experiment_id)
    expsessinfo = request.session.get(expsess_key,{})

    # pdb.set_trace()

    # Check whether this session has already started
    if 'running' in expsessinfo.keys() and expsessinfo['running']:
        # Log the fact that we are resuming a session
        # Serve up the current form using a reverse lookup
        return HttpResponseRedirect(reverse('serve_form', 
            args=(experiment_id,expsessinfo['curr_form_idx'],)))

    # Initialize a session
    expsessinfo.update({
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

    # Check to see whether we are dealing with a special form that requires different handline. This is largely to try to maintain backward compatibility with the legacy PHP version of Ensemble
    form_handler = currform.form_handler
    handler_name = os.path.splitext(form_handler)[0]

    if handler_name == 'form_start_session':
        # We've already done the initialization, so move on to the next form
        expsessinfo['curr_form_idx'] = form_idx+1

        # Update our session storage
        request.session[expsess_key] = expsessinfo

        return HttpResponseRedirect(reverse('serve_form', args=(experiment_id, expsessinfo['curr_form_idx'],)))

    # Define our formset
    QuestionModelFormSet = forms.modelformset_factory(Question, form=QuestionModelForm, extra=0)

    if request.method == 'POST':
        if handler_name == 'form_subject_register':
            form = RegisterSubjectForm(request.POST)
        else:
            form_instance = Form.objects.get(form_id=currform.form_id)
            form = QuestionModelFormSet(request.POST)

        if form.is_valid():
            #
            # Write data to the database. With only a couple of exceptions, based on form_handler, this will be to the response table registered with the experiment
            #


            # Update our visit count
            num_visits = expsessinfo['visit_count'].get(form_idx,0)
            num_visits +=1
            expsessinfo['visit_count'][form_idx] = num_visits

            #
            # Determine where we are going next
            #
            check_conditional = True

            # See whether a break loop flag was set
            break_loop = form.cleaned_data.get('break_loop',False)

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

            # Update our session storage
            request.session[expsess_key] = expsessinfo

            # Move to the next form by calling ourselves
            return HttpResponseRedirect(reverse('serve_form', args=(experiment_id, expsessinfo['curr_form_idx'],)))
            
        # If the form was not valid and we have to present it again, skip the trial running portion of it, so that we only present the questions
        skip_trial = True

    else:
        # Check the conditonal specification on the form we intend to go to, in order to make sure we can go there
        if currform.condition:
            # Parse the condition specification and evaluate it
            # This remains to be implemented 
            return HttpResponseRedirect(reverse('feature_not_enabled'),args=('form conditionals',))

        # Get our blank form
        if handler_name == 'form_subject_register':
            form = RegisterSubjectForm()
        else:
            form_instance = Form.objects.get(form_id=currform.form_id)
            form = QuestionModelFormSet(queryset=form_instance.questions.all())

        skip_trial = False

    # Create our context
    context = {
        'form': form,
        'exf': currform,
       }

    #
    # Additional context variables (these should maybe be part of the form creation, e.g. setting of stimulus_id as a hidden value)
    #

    # Determine what media, if any, we are presenting
    media = {}

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

