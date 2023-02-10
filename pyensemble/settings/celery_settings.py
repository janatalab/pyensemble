# celery_settings.py

import os
from pyensemble.settings.settings import *

LOGGING['handlers']['file']['filename'] = os.path.join(LOG_DIR,'django-debug-celery.txt')

