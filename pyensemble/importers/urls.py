# urls.py

from django.urls import include, path

from pyensemble.importers import views

app_name = 'pyensemble-importers'

urlpatterns = [
    path('', views.import_home, name="import-home"),
    path('stimuli/', views.import_stimuli, name="import-stimuli"),
    path('stimulus/table/', views.import_stimulus_table, name="import-stimulus-table"),
    path('experiment/legacy/', views.import_experiment_structure, name="import-experiment-structure"),
    path('experiment/json/', views.import_experiment_json, name="import-experiment-json"),
]