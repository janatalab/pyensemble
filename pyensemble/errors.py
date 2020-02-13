# errors.py
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest

def feature_not_enabled(request,feature_string):
    HttpResponseBadRequest(f'{feature_string} not enabled')