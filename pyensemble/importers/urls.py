# urls.py

from django.urls import include, path

from pyensemble.importers import views
from pyensemble.importers import definition_views

app_name = 'pyensemble-importers'

urlpatterns = [
    path('', views.import_home, name="import-home"),
    path('stimuli/', views.import_stimuli, name="import-stimuli"),
    path('stimulus/table/', views.import_stimulus_table, name="import-stimulus-table"),
    path('experiment/legacy/', definition_views.import_experiment_structure, name="import-experiment-structure"),
    path('json/', definition_views.import_json, name="import-json"),
]