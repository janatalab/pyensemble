# integrity.py

# Methods for checking integrity of elements of the PyEnsemble infrastructure

from .models import Response, Form

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView

import pdb


'''
Determine whether questions belong to forms in Response table entries
'''
class VerifyResponseFormQuestionMatchView(LoginRequiredMixin, TemplateView):
    template_name = 'pyensemble/integrity/verify_response_form_question_match.html'

    def get_context_data(self, **kwargs):
        context = super(VerifyResponseFormQuestionMatchView, self).get_context_data(**kwargs)

        # Start with a queryset that encompasses all responses
        responses = Response.objects.all()

        context.update({'total_num_responses': responses.count()})

        # Get the responses that are erroneous
        responses = erroneous_response_form_question_match(responses)

        # Use erroneous responses to generate context
        added_context = generate_response_form_question_match_context(responses)

        context.update(added_context)

        # pdb.set_trace()
        return context


def erroneous_response_form_question_match(responses):
    # Determine which forms have been presented
    forms_used = responses.values_list('form', flat=True).distinct()

    # Get those forms, so that we are dealing directly with Form objects
    forms = Form.objects.filter(id__in=forms_used)

    # Iterate over the forms
    for form in forms:
        # Remove valid form, question combinations from the response queryset
        responses = responses.exclude(form=form, question__in=form.question_set.all())

    # What we have left are entries in the response table for which the question does not match the form. Return these
    return responses


def generate_response_form_question_match_context(responses):
    context = {}
    
    # Total number of aberrant entries
    context['num_aberrant_entries'] = responses.count()

    context['experiments'] = responses.values('experiment__id','experiment__title').distinct()
    context['sessions'] = responses.values('session','session__exclude').distinct()
    context['subjects'] = responses.values('subject').distinct()
    context['fxq'] = responses.values('form__name','question__text').distinct()

    return context
