# urls.py

from django.urls import path
from .jingles import import_experiment_structure, delete_exf, import_attributes, import_stims

app_name='jingles'

urlpatterns = [
    path('import_experiment_structure/', import_experiment_structure),
    path('import_stims/', import_stims),
    path('import_attributes/', import_attributes),
    path('delete_exf/<slug:title>/', delete_exf),
]