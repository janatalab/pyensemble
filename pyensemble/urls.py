"""pyensemble URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, reverse

from pyensemble import views
from pyensemble import reporting
from pyensemble import integrity

import pyensemble.errors as error

from pyensemble.experiments import urls as experiment_urls
from pyensemble.importers import urls as importer_urls
from pyensemble.integrations import urls as integrations_urls

# from django.contrib.auth.decorators import login_required

app_name = 'pyensemble'

app_patterns = [
    # path('', RedirectView.as_view(pattern_name='login',permanent=False)),
    path('', views.PyEnsembleHomeView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='pyensemble/login.html'), name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('register/participant/', views.register_participant, name='register-participant'),
    path('register/participant/<int:group_id>/', views.register_participant, name='register_with_group'),
    path('verify-email/<str:user_id>/<str:token>/', views.verify_email, name='verify_email'),
    
    path('stimulus/', views.StimulusView.as_view(template_name='pyensemble/stimulus_base.html'), name='stimulus'),
    path('stimulus/search/', views.StimulusSearchView.as_view(template_name='pyensemble/stimulus_search.html'), name='stimulus-search'),
    path('stimulus/list/', views.StimulusListView.as_view(template_name='pyensemble/stimulus_list_paginated.html'), name='stimulus-list'),

    path('ticket/create/', views.create_ticket, name='create_ticket'),

    path('run/<int:experiment_id>/start/', views.run_experiment, name='run_experiment'),
    path('run/<int:experiment_id>/', views.serve_form, name='serve_form'),    
    path('session/reset/<int:experiment_id>/', views.reset_session, name='reset_session'),
    path('session/flush/', views.flush_session_cache, name='flush_session_cache'),
    path('error/<slug:feature_string>/', error.feature_not_enabled, name='feature_not_enabled'),
    path('record/timezone', views.record_timezone, name='record-timezone'),    
]

editor_patterns = [
    path('', views.EditorView.as_view(template_name='pyensemble/editor_base.html'), name='editor'),
    path('experiments/', views.ExperimentListView.as_view(), name='experiment_list'),
    path('experiments/create/', views.ExperimentCreateView.as_view(), name='experiment_create'),
    path('experiments/copy/<int:experiment_id>/', views.copy_experiment, name='experiment_copy'),
    path('experiments/<int:pk>/', views.ExperimentUpdateView.as_view(), name='experiment_update'),
    path('forms/', views.FormListView.as_view(), name='form_list'),
    path('forms/create/', views.FormCreateView.as_view(), name='form_create'),
    path('forms/update/<int:pk>', views.FormUpdateView.as_view(), name='form_update'),
    path('forms/<int:pk>/', views.FormPresentView.as_view(), name='form_present'),
    path('forms/add/<int:experiment_id>/', views.add_experiment_form, name='add_experiment_form'),
    path('questions/', views.QuestionListView.as_view(), name='question_list'),
    path('questions/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/update/<int:pk>/', views.QuestionUpdateView.as_view(), name='question_update'),
    path('questions/<int:pk>/', views.QuestionPresentView.as_view(), name='question_present'),
    path('questions/add/<int:form_id>/', views.add_form_question, name='add_form_question'),
    path('enums/', views.EnumListView.as_view(), name='enum_list'),
    path('enums/create/', views.EnumCreateView.as_view(), name='enum_create'),
]

reporting_patterns = [
    path('', reporting.index, name='reporting'),
    # path('study/', reporting.study, name='study-reporting'),
    path('study/summary/', reporting.study_summary, name='study-summary'),
   path('study/sessions/', reporting.study_sessions, name='study-sessions'),

    # path('experiment/', reporting.experiment, name='experiment-reporting'),
    path('experiment/summary/', reporting.experiment_summary, name='experiment-summary'),
    path('experiment/responses/', reporting.experiment_responses, name='experiment-responses'),
    path('experiment/sessions/', reporting.experiment_sessions, name='experiment-sessions'),

    path('session/', reporting.session, name='session-reporting'),
    path('session/exclude/', reporting.exclude_session, name='session-exclude'),
    path('session/attach/file/', reporting.attach_session_file, name="attach_session_file"),

    path('subject/exclude/', reporting.exclude_subject, name='subject-exclude'),

]

integrity_patterns = [
    path('verify_response_form_question_match/', integrity.VerifyResponseFormQuestionMatchView.as_view(), name='response_form_question_match'),
]

export_patterns = [
    path('experiment/<int:id>/', views.export_experiment_json, name='export_experiment_json'),
    path('form/<int:id>/', views.export_form_json, name='export_form_json'),
    path('question/<int:id>/', views.export_question_json, name='export_question_json'),

]

# Collect our final set of patterns in the expected urlpatterns

urlpatterns = [
    path('', include(app_patterns)),
    path('group/', include('pyensemble.group.urls', namespace='pyensemble-group')),
    path('editor/', include(editor_patterns)),
    path('experiments/', include(experiment_urls, namespace='experiments')),
    path('reporting/', include(reporting_patterns)),
    path('import/', include(importer_urls, namespace='importers')),
    path('integrations/', include(integrations_urls, namespace='integrations')),
    path('integrity/', include(integrity_patterns)),
    path('export/', include(export_patterns)),
]
