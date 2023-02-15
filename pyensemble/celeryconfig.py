# celeryconfig.py

from datetime import timedelta
#from celery.schedules import crontab

imports = (
    'pyensemble.tasks', 
    ) 

broker_url = 'pyamqp://guest@localhost//'
worker_max_tasks_per_child = 10
task_serializer = 'json'
beat_schedule = {
    'dispatch_notifications': {
        'task': 'pyensemble.tasks.dispatch_notifications',
        'schedule': timedelta(minutes=1),
    },
}