from __future__ import absolute_import, unicode_literals
from pyensemble.celery import app as celery_app

# default_app_config = 'pyensemble.apps.pyensembleConfig'

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.

__all__ = ['celery_app']
