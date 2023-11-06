# urls.py

from django.urls import include, path

from pyensemble.importers import views

app_name = 'pyensemble-importers'

urlpatterns = [
    path('experiment_structure/', views.import_experiment_structure, name="import-experiment-structure"),
    path('stimuli/', views.import_stimuli, name="import-stimuli"),
    path('stimulus/table/', views.import_stimulus_table, name="import-stimulus-table")
]