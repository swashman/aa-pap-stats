"""App settings."""

# Django
from django.apps import apps


def corpstats_active():
    """
    Check if securegroups is installed
    """
    return apps.is_installed("corpstats")
