"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from .keepalive import start_keepalive

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Free Render web services sleep after 15 minutes of inactivity; keep the
# service warm by pinging our own /health/ endpoint from a background thread.
# No-op outside Render (RENDER_EXTERNAL_URL is only set there). The gunicorn
# workers import the app per-process, so each worker runs its own thread —
# harmless, and staggered pings make missed pings less likely.
start_keepalive()
