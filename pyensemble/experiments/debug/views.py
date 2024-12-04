# views.py

from django.conf import settings
from django.shortcuts import render

def home(request):
    template = "debug/home.html"

    # Check if we have a prolific token
    have_prolific = False
    if hasattr(settings, 'PROLIFIC_TOKEN'):
        if settings.PROLIFIC_TOKEN:
            have_prolific = True

    context = {
        'have_prolific': have_prolific,
    }

    return render(request, template, context)