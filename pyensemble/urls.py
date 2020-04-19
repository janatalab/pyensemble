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
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from .views import EditorView, ExperimentListView, FormListView, QuestionListView, ExperimentDetailView, FormDetailView, QuestionDetailView, run_experiment, serve_form, create_question

from pyensemble.tasks import reset_session, create_ticket
import pyensemble.errors as error
from pyensemble import importers

from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='pyensemble/login.html'), name='login'),
    path('', RedirectView.as_view(pattern_name='login',permanent=False)),
    path('editor/', login_required(EditorView.as_view(template_name='pyensemble/editor_base.html')),name='editor'),
    path('experiments/', ExperimentListView.as_view(), name='experiment_list'),
    path('experiments/<int:pk>/', ExperimentDetailView.as_view(), name='experiment_detail'),
    path('experiments/run/<int:experiment_id>/start/',run_experiment, name='run_experiment'),
    path('experiments/run/<int:experiment_id>/',serve_form, name='serve_form'),
    path('form/', FormListView.as_view(), name='form_list'),
    path('form/<int:pk>/', FormDetailView.as_view(), name='form_detail'),
    path('question/create/', create_question, name='create_question'),
    path('question/', QuestionListView.as_view(), name='question_list'),
    path('question/<int:pk>/', QuestionDetailView.as_view(), name='question_detail'),
    path('session/reset/<int:experiment_id>/',reset_session, name='reset_session'),
    path('error/<slug:feature_string>/', error.feature_not_enabled, name='feature_not_enabled'),
    path('ticket/create/', create_ticket, name='create_ticket'),
    path('stimuli/upload/', importers.import_stimuli.import_file),
    path('experiments/', include('pyensemble.experiments.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)