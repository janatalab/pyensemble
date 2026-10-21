"""Isolated test configuration; never connects to deployment services."""

from base64 import urlsafe_b64encode
from pathlib import Path

from django.core.files.storage import FileSystemStorage


BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = 'pyensemble-tests-only'
DEBUG = False
ALLOWED_HOSTS = ['testserver']
ROOT_URLCONF = 'pyensemble.urls'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'crispy_forms',
    'crispy_bootstrap4',
    'django_recaptcha',
    'pyensemble',
    'pyensemble.group',
    'pyensemble.integrations',
]
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'pyensemble.middleware.InterfaceAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
ACCOUNT_INVITATION_ORIGIN = 'https://testserver'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
FIELD_ENCRYPTION_KEY = urlsafe_b64encode(b'0' * 32).decode('ascii')
USE_TZ = True
TIME_ZONE = 'UTC'
SESSION_DURATION = 60 * 60 * 24
PYENSEMBLE_CAPTCHA_ENABLED = False
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
USE_AWS_STORAGE = False
AWS_MEDIA_STORAGE_BUCKET_NAME = 'unused-test-media'
AWS_DATA_STORAGE_BUCKET_NAME = 'unused-test-data'
INSTANCE_LABEL = 'tests'
DEFAULT_FILE_STORAGE = FileSystemStorage
EXPERIMENT_DIR = BASE_DIR / 'pyensemble' / 'experiments'
SITE_ID = 1
SITE_CONFIG_FILE = Path(__file__).with_name('site.ini')
PORT = ''
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = '/'
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap4'
CRISPY_TEMPLATE_PACK = 'bootstrap4'
SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']
