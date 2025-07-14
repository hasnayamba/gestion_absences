import os
from .settings import *
from .settings import BASE_DIR

# Récupération de la SECRET_KEY
SECRET_KEY = os.environ.get('SECRET')
if not SECRET_KEY:
    raise RuntimeError("La variable d'environnement SECRET n'est pas définie.")

# Récupération de l'hôte autorisé pour Azure (ou localhost par défaut)
WEBSITE_HOSTNAME = os.environ.get('WEBSITE_HOSTNAME', 'localhost')
ALLOWED_HOSTS = [WEBSITE_HOSTNAME]

# Protection CSRF (nécessaire en production avec Azure)
CSRF_TRUSTED_ORIGINS = [f"https://{WEBSITE_HOSTNAME}"]

DEBUG = False

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

connection_string = os.environ['AZURE_POSTGRESQL_CONNECTIONSTRING']
parameters = dict(pair.split('=') for pair in connection_string.split(' '))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parameters['dbname'],
        'HOST': parameters['host'],
        'USER': parameters['user'],
        'PASSWORD': parameters['password'],
    }
}
