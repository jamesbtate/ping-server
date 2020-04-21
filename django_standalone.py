"""
Import this module when you need to use Django things outside of a web environment.
Import this module before importing any other module that uses the Django package.

See https://docs.djangoproject.com/en/3.0/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
"""

import os
import django
from django.conf import settings
import pingweb.settings

# settings.configure(pingweb.settings)
os.environ['DJANGO_SETTINGS_MODULE'] = 'pingweb.settings'
django.setup()