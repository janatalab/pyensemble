# cron.py

from .settings import *

LOGGING['handlers'] = {
        'debug-file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'cron-debug.txt'),
            'formatter': 'timestamped',
        }
    }

LOGGING['loggers'] = {
    'django.request': {
            'handlers': ['debug-file'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }