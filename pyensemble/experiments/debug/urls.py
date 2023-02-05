# urls.py
#
# Endpoints for the default debug experiment

from django.urls import path

from . import views, tasks, group

app_name = 'debug'

urlpatterns = [
    path('', views.home, name='home'),
    path('create/experiment/', tasks.create_experiment, name='create-experiment'),
    path('group/create_experiment/', group.create_group_experiment, name='create-group-experiment'),
]