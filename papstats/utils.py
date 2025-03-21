# Third Party
from dateutil.relativedelta import relativedelta

# Django
from django.contrib.auth.models import User
from django.utils.timezone import now

# Alliance Auth
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

logger = get_extension_logger(__name__)


def get_visible_corps(user: User):
    """
    Get corporations visible to a user.
    """
    char = user.profile.main_character

    # Initial filtering based on character ownership
    corps = EveCorporationInfo.objects.all()

    # Superusers and users with view_alliance permission have access to corporations in the same alliance
    if user.is_superuser or user.has_perm("papstats.alliance_access"):
        logger.debug(
            "User is superuser or has view_alliance permission, filtering by alliance."
        )
        # Filter by alliance (superuser or view_alliance permission)
        corps = corps.filter(alliance__alliance_id=char.alliance_id)

    # everyone else can see own corp
    else:
        logger.debug("User has view_corp permission, filtering by corporation.")
        # Filter by the user's corporation if they have permission
        corps = corps.filter(corporation_id=char.corporation_id)

    corps = corps.order_by("corporation_name")  # Add ascending sorting here
    return corps


def get_current_year_month():
    """Returns the current year and month as integers."""
    # we currently don't show live data so need everything to go backwards 1 month
    today = now() - relativedelta(months=1)
    return today.year, today.month


def get_date_context(year: int, month: int):
    """Generates date-related context for menus and data navigation."""
    if year is None or month is None:
        year, month = get_current_year_month()

    current_year, current_month = get_current_year_month()

    return {
        "month": month,
        "month_current": current_month,
        "month_prev": month - 1 if month > 1 else 12,
        "month_next": month + 1 if month < 12 else 1,
        "month_with_year": f"{year}{month:02d}",
        "month_current_with_year": f"{current_year}{current_month:02d}",
        "month_next_with_year": f"{year if month < 12 else year + 1}{(month + 1) if month < 12 else 1:02d}",
        "month_prev_with_year": f"{year if month > 1 else year - 1}{(month - 1) if month > 1 else 12:02d}",
        "year": year,
        "year_current": current_year,
        "year_prev": year - 1,
        "year_next": year + 1,
    }
