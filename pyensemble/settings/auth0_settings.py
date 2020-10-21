# auth0_settings.py

from .settings import *

LOGGING = {}

INSTALLED_APPS += ['auth0login','social_django']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME+'_auth0',
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': DB_HOST,
        'PORT': '3306', # 3306 is the default mysql port
    }
}

# SOCIAL AUTH AUTH0 BACKEND CONFIG
SOCIAL_AUTH_TRAILING_SLASH = False
SOCIAL_AUTH_URL_NAMESPACE = 'auth0:social'

SOCIAL_AUTH_AUTH0_DOMAIN = 'janatalab.us.auth0.com'

with open(os.path.join(PASS_DIR, 'pyensemble_auth0_key.txt')) as f:
    SOCIAL_AUTH_AUTH0_KEY = f.read().strip()

with open(os.path.join(PASS_DIR, 'pyensemble_auth0_secret.txt')) as f:
    SOCIAL_AUTH_AUTH0_SECRET = f.read().strip()

SOCIAL_AUTH_AUTH0_SCOPE = [
    'openid',
    'profile',
    'email'
]

AUDIENCE = None
if os.environ.get('AUTH0_AUDIENCE'):
    AUDIENCE = os.environ.get('AUTH0_AUDIENCE')
else:
    if SOCIAL_AUTH_AUTH0_DOMAIN:
        AUDIENCE = 'https://' + SOCIAL_AUTH_AUTH0_DOMAIN + '/userinfo'
if AUDIENCE:
    SOCIAL_AUTH_AUTH0_AUTH_EXTRA_ARGUMENTS = {'audience': AUDIENCE}

AUTHENTICATION_BACKENDS = {
    'auth0login.auth0backend.Auth0',
    'django.contrib.auth.backends.ModelBackend'
}

# LOGIN_URL = '/login/auth0'
LOGIN_REDIRECT_URL = 'router'