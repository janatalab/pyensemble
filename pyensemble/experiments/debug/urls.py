# urls.py
#
# Endpoints for the default debug experiment

from django.urls import path

from . import views, tasks, group, prolific

app_name = 'debug'

urlpatterns = [
    path('', views.home, name='home'),
    path('create/experiment/', tasks.create_experiment, name='create-experiment'),
    path('group/create_experiment/', group.create_group_experiment, name='create-group-experiment'),
    path('prolific/create_study/', prolific.create_prolific_study, name='create-prolific-study'),
]