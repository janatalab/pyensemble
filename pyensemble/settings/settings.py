"""
Django settings for pyensemble project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import json
from configparser import ConfigParser

import pdb

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Specify the label for this particular installation of PyEnsemble. 
This is effectively the namespace that distinguishes multiple PyEnsemble instances on a single server from each other. 
"""
INSTANCE_LABEL = 'pyensemble'

"""
Specify the path to password and settings files.

The local directory (pyensemble.settings.local) is excluded from git commits and thus a reasonable space to store secrets and credentials associated with this instance.
"""
PASS_DIR = os.path.join(BASE_DIR, 'pyensemble/settings/local')

"""
An example of an alternative location at which to store credentials. Might be useful in production server contexts.
"""
#PASS_DIR = os.path.join('/var/www/private', INSTANCE_LABEL)

# Specify the file that contains our various custom settings and secrets
SITE_CONFIG_FILE = os.path.join(PASS_DIR, 'pyensemble_params.ini')

# Specify the directory where experiments will be located
EXPERIMENT_DIR = os.path.join(BASE_DIR,'pyensemble/experiments')

# Open our configuration file
config = ConfigParser()
config.read(SITE_CONFIG_FILE)

# Get our Django secret
SECRET_KEY = config['django']['secret']

# Specify the list of allowed hosts. Note, these must be specified as a list in the configuration file, with double quotes surrounding each hostname
ALLOWED_HOSTS = json.loads(config['django']['allowed_hosts'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'encrypted_model_fields',
    'captcha',
    'crispy_forms',
    'storages',
    'rest_framework',
    'pyensemble',
    'pyensemble.group',
    'pyensemble.integrations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pyensemble.middleware.TimezoneMiddleware',
]

ROOT_URLCONF = 'pyensemble.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': False, # we actually explicitly turn this on in loaders option
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media', 
            ],
            'loaders': [
                ('django.template.loaders.app_directories.Loader'),
                ('pyensemble.experiments.loaders.Loader',),
            ]
        },
    },
]
CRISPY_TEMPLATE_PACK = 'bootstrap4'

WSGI_APPLICATION = 'pyensemble.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': config['django-db'].get('engine', 'django.db.backends.mysql'),
        'HOST': config['django-db']['host'],
        'NAME': config['django-db']['name'],
        'USER': config['django-db']['user'],
        'PASSWORD': config['django-db']['passwd'],
        'PORT': '3306', # 3306 is the default mysql port
        'OPTIONS': {}
    }
}

# Add ssl info if we are dealing with a MySQL database
ssl_backends = ['django.db.backends.mysql']

if DATABASES['default']['ENGINE'] in ssl_backends:
    if config['django-db'].get('ssl_certpath', None):
        ssl_certpath = config['django-db']['ssl_certpath']
    else:
        ssl_certpath = PASS_DIR

    DATABASES['default']['OPTIONS']['ssl'] = {
        'ca': os.path.join(ssl_certpath, config['django-db']['ssl_certname']),
    }

# Set other mysql specific options
if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    DATABASES['default']['OPTIONS']['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Get the encryption key for the Subject table fields
FIELD_ENCRYPTION_KEY = config['django']['field_encryption_key'] 

# Specify cache engine
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': ['127.0.0.1:11211'],
        'TIMEOUT': 60*60*6,
        'NAME': '',
    },
}

# Specify that we are using the cache for maintaining session info
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_TZ = True
TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

USE_AWS_STORAGE = False

STATIC_ROOT = os.path.join('/var/www/html/static/', INSTANCE_LABEL)
STATIC_URL = f"/static/{INSTANCE_LABEL}/"

MEDIA_ROOT = config['django']['media_root']
MEDIA_URL = config['django']['media_url']

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "thirdparty/"),
]

# SITE stuff
SITE_ID = 1
PORT = ''  # use '' for default http(s) ports

# Login and logout stuff
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = '/'

# Various things pertaining to sessions
SESSION_DURATION=60*60*24 # default session duration

# Email related stuff
if 'email' in config.sections():
    email_params = config['email']

    EMAIL_HOST = email_params['host']
    EMAIL_HOST_USER = email_params['host_user']
    EMAIL_HOST_PASSWORD = email_params['host_password']
    EMAIL_PORT = email_params['port']
    EMAIL_USE_TLS = email_params['use_tls']
    DEFAULT_FROM_EMAIL = email_params['default_from_email']
    SERVER_EMAIL = EMAIL_HOST_USER

# Logging

LOG_DIR = config['django']['logdir']
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'timestamped': {
            'format': '%(levelname)s: %(asctime)s %(module)s %(message)s',
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
            'handlers': ['debug-file','error-file'],
            'propagate': True,
        },
        'django.template': {
            'handlers': ['template-file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'pyensemble': {
            'handlers': ['debug-file', 'error-file'],
            'level': 'DEBUG',
        },
        'pyensemble.experiments': {
            'handlers': ['experiment-debug-file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

#
# Integrations
#

# Google
if 'google' in config.sections():
    NOCAPTCHA = True
    RECAPTCHA_PUBLIC_KEY = config['google']['recaptcha_key']
    RECAPTCHA_PRIVATE_KEY = config['google']['recaptcha_secret']

# AWS
if 'aws' in config.sections():
    aws_params = config['aws']

    USE_AWS_STORAGE = True

    AWS_ACCESS_KEY_ID = aws_params['s3_client_id']
    AWS_SECRET_ACCESS_KEY = aws_params['s3_client_secret']

    AWS_STORAGE_BUCKET_NAME = aws_params['s3_static_bucket_name']
    AWS_S3_CUSTOM_STATIC_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
    AWS_S3_OBJECT_PARAMETERS = {}

    AWS_LOCATION = INSTANCE_LABEL

    STATIC_ROOT = None
    STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_STATIC_DOMAIN, AWS_LOCATION)
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    AWS_MEDIA_STORAGE_BUCKET_NAME = aws_params['s3_media_bucket_name']
    AWS_S3_CUSTOM_MEDIA_DOMAIN = '%s.s3.amazonaws.com' % AWS_MEDIA_STORAGE_BUCKET_NAME

    MEDIA_ROOT = ""
    MEDIA_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_MEDIA_DOMAIN, AWS_LOCATION)

    AWS_DATA_STORAGE_BUCKET_NAME = aws_params['s3_data_bucket_name']


# Spotify
if 'spotify' in config.sections():
    SPOTIFY_CLIENT_ID = config['spotify']['client_id']
    SPOTIFY_CLIENT_SECRET = config['spotify']['client_secret']

# Prolific
if config.has_section('prolific'):
    PROLIFIC_API = config['prolific']['api_endpoint']
    PROLIFIC_TOKEN = config['prolific']['api_token']
    PROLIFIC_WORKSPACE_ID = config['prolific']['workspace_id']
    PROLIFIC_TESTERS = json.loads(config['prolific']['testers'])
