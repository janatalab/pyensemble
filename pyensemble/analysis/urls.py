from django.urls import include, path

from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.index),
    path('sessions/', views.sessions),
    path('sessions/<str:frequency>/', views.sessions),
]