# dev_settings.py

from .settings import *

import pdb

DEBUG=True

INSTALLED_APPS += ['sslserver']

PORT = 8000

# Allow one to connect to an instance running on one's local computer
ALLOWED_HOSTS += ['localhost','127.0.0.1']

# Override the memcached cache backend to use a database table
# Remember to run: python manage.py createcachetable
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'dev_cache_table',
    }
}

# We have to override the possibility that storage of static files is taking place elsewhere, such as AWS S3
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR,'static/')

home = os.environ.get('HOME', None)
if not home:
    home = os.environ.get('HOMEPATH', None)

# Create the log directory
LOG_DIR = os.path.join(home, 'log', INSTANCE_LABEL)
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


# Change logger filenames to reflect the potentially modified LOG_DIR
for handler, value in LOGGING['handlers'].items():
    filename = value['filename']
    value['filename'] = os.path.join(LOG_DIR, os.path.split(filename)[1])
