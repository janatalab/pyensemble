# dev_settings.py

from .settings import *

DEBUG=True

INSTALLED_APPS += ['sslserver']

# Allow one to connect to an instance running on one's local computer
ALLOWED_HOSTS += ['localhost','127.0.0.1']

# We have to override the possibility that storage of static files is taking place elsewhere, such as AWS S3
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR,'static/')

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
