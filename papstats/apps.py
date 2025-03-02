# Django
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

# Pap Stats
from papstats import __version__


class ExampleConfig(AppConfig):
    name = "papstats"
    label = "papstats"
    verbose_name = _(f"Pap Stats v{__version__}")
