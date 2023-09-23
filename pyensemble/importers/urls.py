# urls.py

from django.urls import include, path

from .importers import import_experiment_structure, import_stimulus_table

app_name = 'pyensemble-importers'

urlpatterns = [
    path('experiment_structure/', import_experiment_structure, name="import-experiment-structure"),
    path('stimulus/table/', import_stimulus_table, name="import-stimulus-table")
]