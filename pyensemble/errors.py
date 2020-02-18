# errors.py
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render

def feature_not_enabled(request,feature_string):
    context = {
        'msg': f'{feature_string} not enabled',
        'next': request.session['next'],
    }

    # Clear the session variable for where we're going next
    request.session['next'] = None

    return render(request,'pyensemble/error.html',context)