from django.urls import path

from django.views.generic import TemplateView

from . import views, reports

app_name = 'pyensemble-group'

urlpatterns = [
    path('create/', views.GroupCreateView.as_view(), name='create_group'),
    path('session/start/', views.start_groupsession, name='start_groupsession'),
    path('session/status/', views.groupsession_status, name="groupsession_status"),
    path('session/abort/', views.abort_groupsession, name="abort_groupsession"),
    path('session/end/', views.end_groupsession, name="end_groupsession"),
    path('session/attach/participant/', views.attach_participant, name='attach_participant'),
    path('session/attach/experimenter/', views.attach_experimenter, name='attach_experimenter'),
    path('session/participants/get/', views.get_groupsession_participants, name='get_groupsession_participants'),
    path('participant/state/', views.groupuser_state, name='groupuser_state'),
    path('trial/status/', views.trial_status, name='group_trial_status'),
    path('trial/start/', views.start_trial, name='start_trial'),
    path('trial/end/', views.end_trial, name='end_trial'),
    path('set/client/ready/', views.set_client_ready, name='set_client_ready'),

    path('report/', reports.home, name='report'),
    path('report/experiment/session/selector/', reports.session_selector, name='experiment-session-selector'),
    path('report/experiment/analysis/nav/', TemplateView.as_view(template_name="group/report/experiment_analysis_nav.html"), name='experiment-analysis-nav'),
    path('report/session/detail/', reports.session_detail, name='session-detail'),

]