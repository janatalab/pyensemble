# cron.py

from .settings import *

LOGGING['handlers'].update({
        'cron-info-file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'cron-info.txt'),
            'formatter': 'timestamped',
        },
        'cron-error-file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'cron-error.txt'),
            'formatter': 'timestamped',
        }
    })

LOGGING['loggers'].update({
    'cron-tasks': {
            'handlers': ['cron-info-file', 'cron-error-file'],
            'level': 'INFO',
            'propagate': True,
        }
    })