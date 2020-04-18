# urls.py
#
# Enable experiment specific end-points

from django.urls import path
from .jingles import import_experiment_structure, delete_exf, import_attributes

urlpatterns = [
    path('jingles/import_experiment_structure/', import_experiment_structure),
    path('jingles/import_attributes/', import_attributes),
    path('jingles/delete_exf/<slug:title>/', delete_exf),
]