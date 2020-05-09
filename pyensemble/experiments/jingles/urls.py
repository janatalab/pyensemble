# urls.py

from django.urls import path
from .jingles import delete_exf, import_attributes, import_stims

app_name='jingles'

urlpatterns = [
    path('import_stims/', import_stims),
    path('import_attributes/', import_attributes),
    path('delete_exf/<slug:title>/', delete_exf),
]