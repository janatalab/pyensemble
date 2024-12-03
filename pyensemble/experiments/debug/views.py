# views.py

from django.conf import settings
from django.shortcuts import render

def home(request):
    template = "debug/home.html"

    context = {
        'have_prolific': settings.get('PROLIFIC_TOKEN', None),
    }

    return render(request, template, context)