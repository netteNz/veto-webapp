import os
import django
from django.conf import settings

def pytest_configure(config):
    """Configure Django settings before any tests run."""
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
        django.setup()