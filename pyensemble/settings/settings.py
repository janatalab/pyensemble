"""
Django settings for pyensemble project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from pathlib import Path

import pdb

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Specify the path to password files
PASS_DIR = os.path.dirname('/var/www/private/')

# Specify the directory where experiments will be located
EXPERIMENT_DIR = os.path.join(BASE_DIR,'pyensemble/experiments')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
with open(os.path.join(PASS_DIR, 'pyensemble_django_secret_key.txt')) as f:
    SECRET_KEY = f.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

with open(os.path.join(PASS_DIR, 'pyensemble_allowed_hosts.txt')) as f:
    allowed_host_names = f.read().strip()

# Specify the list of allowed hosts
ALLOWED_HOSTS = [allowed_host_names]

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

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
with open(os.path.join(PASS_DIR, 'pyensemble_db_name.txt')) as f:
    DB_NAME = f.read().strip()

with open(os.path.join(PASS_DIR, 'pyensemble_db_user.txt')) as f:
    DB_USER = f.read().strip()

with open(os.path.join(PASS_DIR, 'pyensemble_db_pass.txt')) as f:
    DB_PASS = f.read().strip()

with open(os.path.join(PASS_DIR, 'pyensemble_db_host.txt')) as f:
    DB_HOST = f.read().strip()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': DB_HOST,
        'PORT': '3306', # 3306 is the default mysql port
    }
}

with open(os.path.join(PASS_DIR, 'pyensemble_django_encryption_key.txt')) as f:
    FIELD_ENCRYPTION_KEY = f.read().strip()

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
    with open(os.path.join(PASS_DIR, 'pyensemble_recaptcha_key.txt')) as f:
        RECAPTCHA_PUBLIC_KEY = f.read().strip()
    with open(os.path.join(PASS_DIR, 'pyensemble_recaptcha_secret.txt')) as f:
        RECAPTCHA_PRIVATE_KEY = f.read().strip()
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

STATIC_ROOT = '/var/www/html/static/'
STATIC_URL = '/static/'

# Pull in any static files defined in our experiment directories
# Get our top-level experiment directory
p = Path(EXPERIMENT_DIR)

# Get our list of experiments
experiment_dirs = [d for d in p.iterdir() if d.is_dir() and d.name != '__pycache__']

# Iterate over the subdirectories
for experiment in experiment_dirs:
    # Check for the existence of a static directory
    static_dir = experiment.joinpath('static')

    if static_dir.exists():
        STATICFILES_DIRS += [str(static_dir)]

# Define where we upload stimuli to
with open(os.path.join(PASS_DIR, 'pyensemble_media_root.txt')) as f:
    MEDIA_ROOT = f.read().strip()

MEDIA_URL = '/ensemble/stimuli/'

# Login and logout stuff
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'editor'
LOGOUT_REDIRECT_URL = '/'

# Various things pertaining to sessions
SESSION_DURATION=60*60*24 # default session duration

LOG_DIR = '/var/log/pyensemble'
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
