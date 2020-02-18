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
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from .views import EditorView, ExperimentListView, FormListView, QuestionListView, ExperimentDetailView, FormDetailView, QuestionDetailView, run_experiment, serve_form
from pyensemble.tasks import reset_session
import pyensemble.errors as error

from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='pyensemble/login.html'), name='login'),
    path('', RedirectView.as_view(pattern_name='login',permanent=False)),
    path('editor/', login_required(EditorView.as_view(template_name='pyensemble/editor_base.html')),name='editor'),
    path('experiments/', ExperimentListView.as_view(), name='experiment_list'),
    path('experiments/<int:pk>/', ExperimentDetailView.as_view(), name='experiment_detail'),
    path('forms/', FormListView.as_view(), name='form_list'),
    path('forms/<int:pk>/', FormDetailView.as_view(), name='form_detail'),
    path('questions/', QuestionListView.as_view(), name='question_list'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question_detail'),
    path('run/<int:experiment_id>/',run_experiment, name='run_experiment'),
    path('run/<int:experiment_id>/<int:form_idx>/',serve_form, name='serve_form'),
    path('session/reset/<int:experiment_id>/',reset_session, name='reset_session'),
    path('error/<slug:feature_string>/', error.feature_not_enabled, name='feature_not_enabled')

    # path('pyensemble/start/<ticket>/', views.start_experiment),
    # path('pyensemble/exf/<form_order_idx>/', views.present_form),
]
