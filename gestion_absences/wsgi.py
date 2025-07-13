"""
WSGI config for gestion_absences project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

settings_module = 'gestion_absences.deployment' if 'WEBSITE_HOSTNAME' in os.environ else 'gestion_absences.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_absences.settings')

application = get_wsgi_application()

