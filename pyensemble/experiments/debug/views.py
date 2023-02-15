# views.py

from django.shortcuts import render

def home(request):
    template = "debug/home.html"

    context = {}

    return render(request, template, context)