"""Models."""

# Django
from django.db import models


class AABasePlugin(models.Model):
    """A meta model for app permissions."""

    class Meta:
        """Meta definitions."""

        managed = False
        default_permissions = ()
        permissions = (("basic_access", "Can access this app"),)
