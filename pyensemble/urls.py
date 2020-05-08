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
from django.contrib import admin
from django.urls import path, include, reverse
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from .views import EditorView, ExperimentListView, ExperimentCreateView, ExperimentUpdateView, FormListView, FormCreateView, FormUpdateView, QuestionListView, QuestionCreateView, QuestionUpdateView, QuestionPresentView, EnumListView, EnumCreateView, run_experiment, serve_form, add_experiment_form, add_form_question, create_ticket, reset_session

import pyensemble.errors as error
from pyensemble import importers

from .experiments import urls as experiment_urls

# from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='pyensemble/login.html'), name='login'),
    path('', RedirectView.as_view(pattern_name='login',permanent=False)),
    path('editor/', EditorView.as_view(template_name='pyensemble/editor_base.html'),name='editor'),
    path('experiments/', ExperimentListView.as_view(), name='experiment_list'),
    path('experiments/create/', ExperimentCreateView.as_view(), name='experiment_create'),
    path('experiments/<int:pk>/', ExperimentUpdateView.as_view(), name='experiment_update'),
    path('experiments/run/<int:experiment_id>/start/',run_experiment, name='run_experiment'),
    path('experiments/run/<int:experiment_id>/',serve_form, name='serve_form'),
    path('forms/', FormListView.as_view(), name='form_list'),
    path('forms/create/', FormCreateView.as_view(), name='form_create'),
    path('forms/<int:pk>/', FormUpdateView.as_view(), name='form_update'),
    path('forms/add/<int:experiment_id>/', add_experiment_form, name='add_experiment_form'),
    path('questions/', QuestionListView.as_view(), name='question_list'),
    path('questions/create/', QuestionCreateView.as_view(), name='question_create'),
    path('questions/update/<int:pk>/', QuestionUpdateView.as_view(), name='question_update'),
    path('questions/<int:pk>/', QuestionPresentView.as_view(), name='question_present'),
    path('questions/add/<int:form_id>/', add_form_question, name='add_form_question'),
    path('enums/', EnumListView.as_view(), name='enum_list'),
    path('enums/create/', EnumCreateView.as_view(), name='enum_create'),
    path('session/reset/<int:experiment_id>/',reset_session, name='reset_session'),
    path('error/<slug:feature_string>/', error.feature_not_enabled, name='feature_not_enabled'),
    path('ticket/create/', create_ticket, name='create_ticket'),
    path('stimuli/upload/', importers.import_stimuli.import_file),
    # Add user specific experiment URLs
    path('experiments/', include(experiment_urls, namespace='experiments')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)