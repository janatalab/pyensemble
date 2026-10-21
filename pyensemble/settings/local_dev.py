"""Self-contained, local-only settings for PyEnsemble development."""

import base64
import hashlib
import os
import secrets
from pathlib import Path

from django.core.files.storage import FileSystemStorage


BASE_DIR = Path(__file__).resolve().parents[2]
LOCAL_STATE_DIR = Path(
    os.environ.get('PYENSEMBLE_LOCAL_STATE_DIR', BASE_DIR / '.local'),
).expanduser().resolve()
LOCAL_STATE_DIR.mkdir(parents=True, exist_ok=True)


def _get_local_secret_key():
    configured_key = os.environ.get('PYENSEMBLE_LOCAL_SECRET_KEY')
    if configured_key:
        return configured_key

    key_file = LOCAL_STATE_DIR / 'secret_key'
    try:
        descriptor = os.open(
            key_file,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        key = key_file.read_text(encoding='utf-8').strip()
        if not key:
            raise RuntimeError(
                f'Local Django secret key file is empty: {key_file}',
            )
        return key

    key = secrets.token_urlsafe(50)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as key_file_handle:
        key_file_handle.write(key)
        key_file_handle.flush()
        os.fsync(key_file_handle.fileno())
    return key


SECRET_KEY = _get_local_secret_key()
FIELD_ENCRYPTION_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(
        b'pyensemble-local-field-encryption:' + SECRET_KEY.encode('utf-8'),
    ).digest(),
).decode('ascii')

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
ROOT_URLCONF = 'pyensemble.urls'
WSGI_APPLICATION = 'pyensemble.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
AUTH_USER_MODEL = 'auth.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'encrypted_model_fields',
    'django_recaptcha',
    'crispy_forms',
    'crispy_bootstrap4',
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
    'pyensemble.middleware.InterfaceAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pyensemble.middleware.TimezoneMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
            'loaders': [
                'django.template.loaders.app_directories.Loader',
                ('pyensemble.experiments.loaders.Loader',),
            ],
        },
    },
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap4'
CRISPY_TEMPLATE_PACK = 'bootstrap4'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': LOCAL_STATE_DIR / 'pyensemble.sqlite3',
    },
}

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]
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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
USE_L10N = True

INSTANCE_LABEL = 'pyensemble-local'
EXPERIMENT_DIR = BASE_DIR / 'pyensemble' / 'experiments'
SITE_ID = 1
SITE_CONFIG_FILE = Path(__file__).with_name('local_dev.ini')
PORT = 8000
SESSION_DURATION = 60 * 60 * 24

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_INVITATION_ORIGIN = os.environ.get(
    'PYENSEMBLE_ACCOUNT_INVITATION_ORIGIN',
    'http://localhost:8000',
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'pyensemble-local@localhost'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

USE_AWS_STORAGE = False
DEFAULT_FILE_STORAGE = FileSystemStorage
MEDIA_ROOT = LOCAL_STATE_DIR / 'media'
MEDIA_URL = '/media/'
STATIC_ROOT = LOCAL_STATE_DIR / 'static'
STATIC_URL = '/static/'
THIRDPARTY_DIR = BASE_DIR / 'thirdparty'
STATICFILES_DIRS = [THIRDPARTY_DIR] if THIRDPARTY_DIR.is_dir() else []
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'OPTIONS': {'location': str(MEDIA_ROOT)},
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        'OPTIONS': {'location': str(STATIC_ROOT)},
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pyensemble-local',
    },
}

PYENSEMBLE_CAPTCHA_ENABLED = False
PYENSEMBLE_EMAIL_BACKEND = EMAIL_BACKEND
SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']

AWS_MEDIA_STORAGE_BUCKET_NAME = ''
AWS_DATA_STORAGE_BUCKET_NAME = ''
SPOTIFY_CLIENT_ID = ''
SPOTIFY_CLIENT_SECRET = ''
PROLIFIC_API = ''
PROLIFIC_TOKEN = ''
PROLIFIC_WORKSPACE_ID = ''
PROLIFIC_TESTER_IDS = []

LOG_DIR = LOCAL_STATE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'pyensemble': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
