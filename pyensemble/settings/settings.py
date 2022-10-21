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

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# What is our label for this particular installation of PyEnsemble. This is what helps to distinguish multiple PyEnsemble instances on a single server from each other. Make sure to use a trailing slash.
INSTANCE_LABEL = 'pyensemble/'

# Specify the path to password files
PASS_DIR = os.path.dirname(os.path.join('/var/www/private', INSTANCE_LABEL))

# Specify the directory where experiments will be located
EXPERIMENT_DIR = os.path.join(BASE_DIR,'pyensemble/experiments')

# Open our configuration file
config = ConfigParser()
config.read(os.path.join(PASS_DIR, 'pyensemble_params.ini'))

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
    'encrypted_model_fields',
    'captcha',
    'crispy_forms',
    'pyensemble',
    'pyensemble.group',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': config['django-db']['host'],
        'NAME': config['django-db']['name'],
        'USER': config['django-db']['user'],
        'PASSWORD': config['django-db']['passwd'],
        'PORT': '3306', # 3306 is the default mysql port
        'OPTIONS': {
            'ssl': {
                'ca': config['django-db']['ssl_certpath'],
            },
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Get the encryption key for the Subject table fields
FIELD_ENCRYPTION_KEY = config['django']['field_encryption_key'] 

# Specify cache engine
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
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

# Google reCaptcha
try:
    NOCAPTCHA = True
    RECAPTCHA_PUBLIC_KEY = config['google']['recaptcha_key']
    RECAPTCHA_PRIVATE_KEY = config['google']['recaptcha_secret']
except:
    pass

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "thirdparty/"),
]


STATIC_ROOT = os.path.join('/var/www/html/static/', INSTANCE_LABEL)
STATIC_URL = '/static/'+INSTANCE_LABEL

MEDIA_ROOT = config['django']['media_root']
MEDIA_URL = config['django']['media_url']

# Login and logout stuff
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'editor'
LOGOUT_REDIRECT_URL = '/'

# Various things pertaining to sessions
SESSION_DURATION=60*60*24 # default session duration

LOG_DIR = config['django']['logdir']
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'timestamped': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
    },
    'handlers': {
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
        }
    },
}
