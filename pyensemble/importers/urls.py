# urls.py

from django.urls import include, path

from .importers import import_experiment_structure

app_name = 'importers'

urlpatterns = [
    path('import_experiment_structure/', import_experiment_structure),
]