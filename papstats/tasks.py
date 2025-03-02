"""Tasks."""

# Third Party
from celery import shared_task

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


@shared_task
def my_task():
    """An example task."""
