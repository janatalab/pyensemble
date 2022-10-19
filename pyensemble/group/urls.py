from django.urls import path

from .views import GroupCreateView, start_groupsession, groupsession_status, abort_groupsession, end_groupsession, attach_participant, attach_experimenter, get_groupsession_participants, trial_status, start_trial, end_trial

app_name = 'pyensemble-group'

urlpatterns = [
    path('create/', GroupCreateView.as_view(), name='create_group'),
    path('session/start/', start_groupsession, name='start_groupsession'),
    path('session/status/', groupsession_status, name="groupsession_status"),
    path('session/abort/', abort_groupsession, name="abort_groupsession"),
    path('session/end/', end_groupsession, name="end_groupsession"),
    path('session/attach/participant/', attach_participant, name='attach_participant'),
    path('session/attach/experimenter/', attach_experimenter, name='attach_experimenter'),
    path('session/participants/get/', get_groupsession_participants, name='get_groupsession_participants'),
    path('trial/status/', trial_status, name='group_trial_status'),
    path('trial/start/', start_trial, name='start_trial'),
    path('trial/end/', end_trial, name='end_trial'),
]