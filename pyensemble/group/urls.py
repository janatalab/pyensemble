from django.urls import path

from django.views.generic import TemplateView

from . import views

app_name = 'pyensemble-group'

urlpatterns = [
    path('create/', views.GroupCreateView.as_view(), name='create_group'),
    path('members/<int:id>/', views.GroupMemberListView.as_view(), name='group_members'),
    
    path('session/start/', views.start_groupsession, name='start_groupsession'),
    path('session/status/', views.groupsession_status, name="groupsession_status"),
    path('session/exit_loop/', views.exit_loop, name="exit_loop"),
    path('session/abort/', views.abort_groupsession, name="abort_groupsession"),
    path('session/end/', views.end_groupsession, name="end_groupsession"),

    path('session/exclude/', views.exclude_groupsession, name="exclude_groupsession"),

    path('session/attach/participant/', views.attach_participant, name='attach_participant'),
    path('session/attach/experimenter/', views.attach_experimenter, name='attach_experimenter'),
    
    path('session/participants/get/', views.get_groupsession_participants, name='get_groupsession_participants'),

    path('participant/state/get/', views.groupuser_state, name='groupuser_state'),
    path('participant/state/wait/', views.wait_groupuser_state, name='wait_groupuser_state'),
    path('participant/exit/loop/', views.groupuser_exitloop, name='groupuser_exitloop'),

    path('trial/status/', views.trial_status, name='group_trial_status'),
    path('trial/start/', views.start_trial, name='start_trial'),
    path('trial/end/', views.end_trial, name='end_trial'),
    path('set/client/ready/', views.set_client_ready, name='set_client_ready'),

]