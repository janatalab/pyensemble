# urls.py
#
# Endpoints for the default debug experiment

from django.urls import path

from . import group

app_name = 'debug'

urlpatterns = [
    path('group/create_experiment/', group.create_experiment),
]