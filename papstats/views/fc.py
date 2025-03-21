"""Views."""

# Standard Library
import base64
import calendar
from io import BytesIO

# Third Party
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import BadRequest, PermissionDenied
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.timezone import now

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# Pap Stats
from papstats.models import MonthlyCreatorStats, MonthlyFleetType
from papstats.utils import get_date_context, get_visible_corps

logger = get_extension_logger(__name__)
CHART_BACKGROUND_COLOR = "#575555"
months_to_display = 5


def get_navbar_elements(user: User):
    avail = get_visible_corps(user)
    logger.debug(f"Available corps: {avail}")
    return {
        "available": avail,
    }


@login_required
@permission_required("papstats.basic_access")
def fc(request: HttpRequest, year: int = None, month: int = None) -> HttpResponse:
    """Handles fleet commander (fc) related views with optional parameters."""
    context = {
        **get_date_context(year, month),  # Adds all date-related values
        **get_navbar_elements(request.user),
    }
    return render(request, "papstats/fc.html", context)


@login_required
def fc_data(request: HttpRequest, year: int, month: int) -> HttpResponse:
    """Handles corporation-related views with optional parameters."""
    if not request.headers.get("HX-Request"):
        raise PermissionDenied("No Direct Access!")

        # Query data from MonthlyCreatorStats
    stats = MonthlyCreatorStats.objects.filter(month=month, year=year)
    fleet_types = MonthlyFleetType.objects.filter(source="afat", month=month, year=year)
    if stats.count() == 0:
        return render(
            request,
            "papstats/fc_data.html",
            {"staterror": "No stats for selected corp or date"},
        )
    creators = set()
    for stat in stats:
        # Log the ID of the stat
        logger.info(f"Logging stat ID: {stat.creator_id}")

        # Check if main_character exists; otherwise, use username
        creator_name = (
            stat.get_creator().profile.main_character.character_name
            if stat.get_creator().profile.main_character
            else stat.get_creator().username
        )
        creators.add(creator_name)

    creators = list(creators)
    data = {fleet_type.name: [0] * len(creators) for fleet_type in fleet_types}
    for stat in stats:
        if stat.fleet_type.source == "afat":
            # Check if main_character exists; otherwise, use username
            creator_name = (
                stat.get_creator().profile.main_character.character_name
                if stat.get_creator().profile.main_character
                else stat.get_creator().username
            )
            data[stat.fleet_type.name][
                creators.index(creator_name)
            ] += stat.total_created

    df = pd.DataFrame(data, index=creators)
    df = df.sort_index()

    # Initialize base64 strings
    image_base64 = ""
    pie_image_base64 = ""
    line_chart_base64 = ""

    if not df.empty:
        # Remove columns with all zeros
        df = df.loc[:, (df != 0).any(axis=0)]

        if not df.empty:
            colormap = plt.cm.viridis
            color_range = colormap(np.linspace(0, 1, len(df.columns)))

            plt.figure(figsize=(12, 8))
            ax = df.plot(kind="bar", stacked=True, figsize=(12, 8), color=color_range)
            ax.set_facecolor(CHART_BACKGROUND_COLOR)
            plt.gcf().set_facecolor(CHART_BACKGROUND_COLOR)
            plt.ylabel("Total Created", color="lightgray")
            plt.title(
                f"Fleet Types By FC for {calendar.month_name[month]} {year}",
                color="white",
                fontsize="16",
                fontweight="bold",
            )
            plt.xticks(rotation=45, ha="right", color="white")
            plt.yticks(color="white")
            plt.legend(
                facecolor="#2c2f33",
                edgecolor="white",
                title_fontsize="13",
                fontsize="11",
                labelcolor="lightgray",
            )
            plt.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, prune="both"))
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.clf()
            plt.close()

        total_created_by_fleet = (
            stats.filter(fleet_type__source="afat")
            .values("fleet_type__name")
            .annotate(total_created=Sum("total_created"))
            .order_by("fleet_type__name")
        )
        fleet_types = [item["fleet_type__name"] for item in total_created_by_fleet]
        proportions = [item["total_created"] for item in total_created_by_fleet]

        if proportions:
            pie_color_range = colormap(np.linspace(0, 1, len(fleet_types)))

            plt.figure(figsize=(8, 8))
            wedges, texts, autotexts = plt.pie(
                proportions,
                autopct="%1.1f%%",
                startangle=140,
                colors=pie_color_range,
                pctdistance=0.85,
            )
            plt.setp(texts, color="white")
            plt.setp(autotexts, color="black")
            plt.gcf().set_facecolor(CHART_BACKGROUND_COLOR)
            plt.legend(
                wedges,
                fleet_types,
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                facecolor="#2c2f33",
                edgecolor="white",
                title_fontsize="13",
                fontsize="11",
                labelcolor="lightgray",
            )
            plt.title(
                f"Fleet Type Proportions for {calendar.month_name[month]} {year}",
                color="white",
                fontsize="16",
                fontweight="bold",
            )
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            pie_image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.clf()
            plt.close()

    # Line chart for total fleets of each type each month
    start_month = (month - months_to_display) % 12 or 12
    start_year = year if month >= months_to_display else year - 1
    date_range = [
        (start_year + (start_month + i - 1) // 12, (start_month + i - 1) % 12 + 1)
        for i in range(months_to_display + 1)
    ]

    monthly_totals = (
        MonthlyCreatorStats.objects.filter(
            year__in=[start_year, year],
            month__in=[date[1] for date in date_range],
        )
        .values("month", "year", "fleet_type__name")
        .annotate(total_fleets=Sum("total_created"))
        .order_by("year", "month", "fleet_type__name")
    )

    fleet_type_names = {item["fleet_type__name"] for item in monthly_totals}
    line_data = {name: [0] * len(date_range) for name in fleet_type_names}
    for item in monthly_totals:
        fleet_name = item["fleet_type__name"]
        date_index = next(
            (
                i
                for i, date in enumerate(date_range)
                if date[1] == item["month"] and date[0] == item["year"]
            ),
            None,
        )
        if date_index is not None:
            line_data[fleet_name][date_index] = item["total_fleets"]

    if line_data:
        plt.figure(figsize=(12, 8))
        colors = plt.cm.viridis(np.linspace(0, 1, len(line_data)))  # Use colormap

        for (fleet_name, totals), color in zip(line_data.items(), colors):
            plt.plot(
                range(1, len(date_range) + 1),
                totals,
                marker="o",
                label=fleet_name,
                color=color,
            )

        plt.gcf().set_facecolor(CHART_BACKGROUND_COLOR)
        ax = plt.gca()
        ax.set_facecolor(CHART_BACKGROUND_COLOR)  # Set plot area background color
        plt.title(
            f"Month Over Month Fleet Types for {year}",
            color="white",
            fontsize=16,
            fontweight="bold",
        )
        plt.ylabel("Total Fleets", color="white")
        plt.xticks(
            ticks=range(1, len(date_range) + 1),
            labels=[f"{calendar.month_abbr[date[1]]} {date[0]}" for date in date_range],
            color="white",
            rotation=45,  # Set rotation for the labels
            ha="right",  # Align labels to the right
        )
        plt.yticks(color="white")
        plt.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
        plt.legend(
            loc="upper left",
            facecolor="#2c2f33",
            edgecolor="white",
            labelcolor="lightgray",
        )
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        line_chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        plt.clf()
        plt.close()

    context = {
        "bar_chart": image_base64,
        "pie_chart": pie_image_base64,
        "line_chart": line_chart_base64,
    }

    return render(request, "papstats/fc_data.html", context)
