"""
WSGI config for veto project for Elastic Beanstalk.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.
"""

import os
import sys

# Add the 'server' directory to Python path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()