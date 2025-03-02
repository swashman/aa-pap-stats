"""App settings."""

# Django
from django.conf import settings

EXAMPLE_SETTING_ONE = getattr(settings, "EXAMPLE_SETTING_ONE", None)
