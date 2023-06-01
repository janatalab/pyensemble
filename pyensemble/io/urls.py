from django.urls import path

from . import views

app_name = 'pyensemble-io'

urlpatterns = [
    path('', views.home, name='home'),
    path('parallel/send/code/', views.send_code, name='send-code'),
    path('parallel/test/timing/', views.test_timing, name='test-timing'),
    path('parallel/test/timing/run/', views.run_timing_test, name='run-timing-test'),
    path('parallel/test/end/', views.end_test, name='end-test'),
]