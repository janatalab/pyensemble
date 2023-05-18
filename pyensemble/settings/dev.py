# dev_settings.py

from .settings import *

DEBUG=True

INSTALLED_APPS += ['sslserver']

home = os.environ.get('HOME', None)
if not home:
    home = os.environ.get('HOMEPATH', None)

LOG_DIR = os.path.join(home,'log')
if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'timestamped': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
        'experiment': {
            'format': '%(levelname)s: %(asctime)s %(pathname)s (%(funcName)s): %(message)s',
        }
    },
    'handlers': {
        'experiment-debug-file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'experiment-debug.txt'),
            'formatter': 'experiment',
        },
        'debug-file': {
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
        },
        'template-file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR,'django-template.txt'),
            'formatter': 'timestamped',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['error-file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['debug-file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.template': {
            'handlers': ['template-file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'pyensemble.experiments': {
            'handlers': ['experiment-debug-file'],
            'level': 'DEBUG',
            'propagate': True,
        }
    },
}
