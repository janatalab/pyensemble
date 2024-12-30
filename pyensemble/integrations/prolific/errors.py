# Define a prolific_error method
from django.http import HttpResponseBadRequest

from django.template.loader import get_template

def prolific_error(request, error_type):
    # Load the template
    template = get_template("pyensemble/integrations/prolific/prolific_error.html")

    # Set the context
    if error_type == "PROLIFIC_API_ERROR":
        error_msg = "There was an error with the Prolific API"

    elif error_type == "PROLIFIC_API_NOT_FOUND":
        error_msg = "The Prolific API was not found"

    elif error_type == "PROLIFIC_API_NOT_ENABLED":
        error_msg = "The Prolific API is not enabled"

    elif error_type == "NO_STUDY_ID":
        error_msg = "No study ID was provided"

    else:
        error_msg = "Unspecified Prolific API error"

    context = {
        'error_type': error_type,
        'error_msg': error_msg,
    }

    # Render the template
    response = template.render(context)

    # Return the error page
    return HttpResponseBadRequest(response)