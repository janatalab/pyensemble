# dev_settings.py

from .settings import *

DEBUG=True

INSTALLED_APPS += ['sslserver']

LOG_DIR = os.path.join(os.environ['HOME'],'log')
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'timestamped': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'django-debug.txt'),
            'formatter': 'timestamped',
        },
        'error-file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'django-error.txt'),
            'formatter': 'timestamped',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['file','error-file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
