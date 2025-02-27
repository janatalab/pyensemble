# urls.py
#
# Endpoints for the default debug experiment

from django.urls import path

from . import views, tasks, group, prolific

app_name = 'debug'

urlpatterns = [
    path('', views.home, name='home'),
    path('create/experiment/with_notification/', tasks.create_experiment_with_notification, name='create-experiment-with-notification'),
    path('create/experiment/with_email_login/', tasks.create_experiment_with_email_login, name='create-experiment-with-email-login'),
    path('create/experiment/group/', group.create_group_experiment, name='create-group-experiment'),
    path('prolific/', prolific.home, name='prolific-home'),
    path('prolific/create/experiment/multiday/', prolific.create_multiday_example, name='create-prolific-multiday'),
    path('prolific/register/test/subject/', prolific.register_test_subject, name='register-prolific-test-subject'),
    path('prolific/create/experiment/multiday/publish/', prolific.publish_multiday_example, name='publish-prolific-multiday'),
    path('prolific/delete/multiday/', prolific.delete_multiday_example, name='prolific-delete-multiday'),
    path('prolific/delete/pyensemble/', prolific.delete_pyensemble_example, name='prolific-delete-pyensemble'),
]