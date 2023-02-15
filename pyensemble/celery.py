# celery.py
from __future__ import absolute_import, unicode_literals

import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
# We need to override the default settings module so that the debug file path for celery doesn't collide with that created by wsgi in production
os.environ['DJANGO_SETTINGS_MODULE'] = 'pyensemble.settings.celery_settings'

app = Celery('pyensemble')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('pyensemble.celeryconfig')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)

def debug_task(self):
    print(('Request: {0!r}'.format(self.request)))
