# errors.py
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render

from django.template.loader import get_template

import pdb


def feature_not_enabled(request,feature_string):
    context = {
        'msg': f'{feature_string} not enabled',
        'next': request.session['next'],
    }

    # Clear the session variable for where we're going next
    request.session['next'] = None

    return render(request,'pyensemble/error.html',context)

def ticket_error(request, ticket, error_type):
    # Load the template
    template = get_template("pyensemble/errors/ticket.html")

    # Set the context
    if error_type == "TICKET_MISSING":
        error_msg = "A ticket is required to start the experiment"

    elif error_type == "TICKET_NOT_FOUND":
        error_msg = "A ticket with this code was not found"

    elif error_type == "TICKET_EXPERIMENT_MISMATCH":
        error_msg = "This ticket is not valid for this experiment"

    elif error_type == "TICKET_ALREADY_USED":   
        error_msg = "This ticket has already been used" 

    elif error_type == "TICKET_EXPIRED":   
        error_msg = "This ticket has expired" 

    else:
        error_msg = "Unspecified ticket error"

    context = {
        'error_type': error_type,
        'error_msg': error_msg,
        'ticket': ticket,
    }

    # Render the template
    response = template.render(context)

    # Return the error page
    return HttpResponseBadRequest(response)