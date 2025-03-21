"""Views."""

# flake8: noqa: E402
# Standard Library
import base64
import calendar
from collections import defaultdict
from datetime import datetime
from io import BytesIO

# Third Party
import matplotlib

matplotlib.use("Agg")
# Third Party
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Django
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

# Alliance Auth
from allianceauth.authentication.models import UserProfile
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

# Pap Stats
from papstats.models import MonthlyCorpStats, MonthlyFleetType, MonthlyUserStats
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
def corporation(
    request: HttpRequest, corpid: int = None, year: int = None, month: int = None
) -> HttpResponse:
    """Handles corporation-related views with optional parameters."""
    if corpid is None:
        corpid = request.user.profile.main_character.corporation_id
    corp = EveCorporationInfo.objects.get(corporation_id=corpid)
    # Base response data
    context = {
        "corporation": corp.corporation_name,
        "corpid": corpid,
        **get_date_context(year, month),  # Adds all date-related values
        **get_navbar_elements(request.user),
    }

    return render(
        request, "papstats/corporation.html", context
    )  # Assuming you have a template named `corporation.html`


@login_required
def corporation_data(
    request: HttpRequest, corpid: int, year: int, month: int
) -> HttpResponse:
    """Handles corporation-related views with optional parameters."""
    if not request.headers.get("HX-Request"):
        raise PermissionDenied("No Direct Access!")

    try:
        corp = EveCorporationInfo.objects.get(corporation_id=corpid)
    except EveCorporationInfo.DoesNotExist:
        return render(
            request,
            "papstats/alliance_data.html",
            {"staterror": "Could not find corp"},
        )

    corp_members = UserProfile.objects.filter(
        main_character__corporation_id=corp.corporation_id
    ).order_by("main_character__character_name")

    users = [member.main_character.character_name for member in corp_members]
    user_ids = [member.user_id for member in corp_members]

    stats = MonthlyUserStats.objects.filter(
        user_id__in=user_ids, month=month, year=year
    ).select_related("fleet_type")

    if stats.count() == 0:
        return render(
            request,
            "papstats/corporation_data.html",
            {"staterror": "No stats for selected corp or date"},
        )

    data_afat = {
        user: {
            ft.name: 0
            for ft in MonthlyFleetType.objects.filter(
                source="afat", month=month, year=year
            )
        }
        for user in users
    }
    data_imp = {
        user: {
            f"IMP {ft.name}": 0
            for ft in MonthlyFleetType.objects.filter(
                source="imp", month=month, year=year
            )
        }
        for user in users
    }

    for stat in stats:
        character_name = stat.get_user().profile.main_character.character_name
        if stat.fleet_type.source == "afat":
            data_afat[character_name][stat.fleet_type.name] += stat.total_fats
        elif stat.fleet_type.source == "imp":
            data_imp[character_name][f"IMP {stat.fleet_type.name}"] += stat.total_fats

    df_afat = pd.DataFrame(data_afat).T
    df_imp = pd.DataFrame(data_imp).T
    df_afat = df_afat.loc[:, (df_afat != 0).any(axis=0)]
    df_imp = df_imp.loc[:, (df_imp != 0).any(axis=0)]
    logger.info(df_afat)
    if not df_afat.empty or not df_imp.empty:
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
        ax.set_facecolor(CHART_BACKGROUND_COLOR)

        bar_width = 0.35
        indices = np.arange(len(users))

        bottom_afat = np.zeros(len(users))
        bottom_imp = np.zeros(len(users))
        colors_afat = plt.cm.viridis(np.linspace(0, 1, len(df_afat.columns)))
        colors_imp = plt.cm.cool(np.linspace(0, 1, len(df_imp.columns)))

        for idx, column in enumerate(df_afat.columns):
            ax.bar(
                indices - bar_width / 2,
                df_afat[column].values,
                bar_width,
                bottom=bottom_afat,
                color=colors_afat[idx],
                label=column,
            )
            bottom_afat += df_afat[column].values

        for idx, column in enumerate(df_imp.columns):
            ax.bar(
                indices + bar_width / 2,
                df_imp[column].values,
                bar_width,
                bottom=bottom_imp,
                color=colors_imp[idx],
                label=column,
            )
            bottom_imp += df_imp[column].values

        ylim_bottom, ylim_top = ax.get_ylim()
        if ylim_top < 5:
            ax.set_ylim(0, 5)
        else:
            max_y = max(bottom_afat.max(), bottom_imp.max())
            ax.set_ylim(0, max_y * 1.1)

        for i, total in enumerate(bottom_afat):
            if total > 0:
                ax.text(
                    i - bar_width / 2,
                    total,
                    f"{int(total)}",
                    ha="center",
                    va="bottom",
                    color="white",
                )

        for i, total in enumerate(bottom_imp):
            if total > 0:
                ax.text(
                    i + bar_width / 2,
                    total,
                    f"{int(total)}",
                    ha="center",
                    va="bottom",
                    color="white",
                )

        ax.set_title(
            f"{corp.corporation_name} Fleet Breakdown for {calendar.month_name[month]} {year}",
            color="white",
            fontsize=16,
            fontweight="bold",
        )
        ax.set_ylabel("Total Fats", color="white")
        ax.set_xticks(indices)
        ax.set_xticklabels(users, rotation=45, ha="right", color="white")
        ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
        ax.tick_params(axis="y", colors="lightgray")
        ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        bar_chart = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        plt.clf()
        plt.close()
    else:
        # Placeholder chart for corporations with no fats
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
        ax.set_facecolor(CHART_BACKGROUND_COLOR)

        ax.text(
            0.5,
            0.5,
            "No Fats Data Available",
            ha="center",
            va="center",
            color="white",
            fontsize=16,
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(
            f"{corp.corporation_name} Fleet Breakdown for {calendar.month_name[month]} {year}",
            color="white",
        )
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        bar_chart = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        plt.clf()
        plt.close()

    # Line chart for month over month AFAT and IMP data for each corp
    afat_stats = (
        MonthlyCorpStats.objects.filter(
            corporation_id=corp.corporation_id,
            fleet_type__source="afat",
        )
        .values("year", "month")
        .annotate(total=Sum("total_fats"))
        .order_by("year", "month")
    )

    imp_stats = (
        MonthlyCorpStats.objects.filter(
            corporation_id=corp.corporation_id,
            fleet_type__source="imp",
        )
        .values("year", "month")
        .annotate(total=Sum("total_fats"))
        .order_by("year", "month")
    )

    start_month = (month - months_to_display) % 12 or 12
    start_year = year if month >= months_to_display else year - 1
    date_range = [
        (start_year + (start_month + i - 1) // 12, (start_month + i - 1) % 12 + 1)
        for i in range(months_to_display + 1)
    ]
    date_totals_afat = {date: 0 for date in date_range}
    date_totals_imp = {date: 0 for date in date_range}
    for item in afat_stats:
        date_totals_afat[(item["year"], item["month"])] = item["total"]
    for item in imp_stats:
        date_totals_imp[(item["year"], item["month"])] = item["total"]

    # Ensure both lists are the same length by aligning data
    dates = [datetime(year=year, month=month, day=1) for year, month in date_range]
    totals_afat = [date_totals_afat.get((date.year, date.month), 0) for date in dates]
    totals_imp = [date_totals_imp.get((date.year, date.month), 0) for date in dates]

    running_avg_afat = pd.Series(totals_afat).rolling(window=3, min_periods=1).mean()
    running_avg_imp = pd.Series(totals_imp).rolling(window=3, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.plot(dates, totals_afat, marker="o", color="cyan", label="Total Fats")
    ax.plot(
        dates,
        running_avg_afat,
        linestyle="--",
        color="orange",
        label="Running Avg",
    )
    ax.plot(dates, totals_imp, marker="o", color="blue", label="IMP Total Fats")
    ax.plot(
        dates,
        running_avg_imp,
        linestyle="--",
        color="purple",
        label="IMP Running Avg",
    )

    for i, total in enumerate(totals_afat):
        if total > 0:
            ax.text(
                dates[i],
                total,
                f"{total}",
                ha="center",
                va="bottom",
                color="white",
                fontsize=10,
            )

    for i, total in enumerate(totals_imp):
        if total > 0:
            ax.text(
                dates[i],
                total,
                f"{total}",
                ha="center",
                va="bottom",
                color="white",
                fontsize=10,
            )

    ax.set_ylim(0)  # Ensure y-axis starts at zero
    ax.yaxis.get_major_locator().set_params(integer=True)  # Display only integer ticks
    ax.set_title(
        f"{corp.corporation_name} Month Over Month",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Fats", color="lightgray")
    ax.tick_params(axis="y", colors="lightgray")
    ax.tick_params(axis="x", colors="lightgray", rotation=45)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    line_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close()

    # RAW DATA
    raw_data = {}
    user_data = []

    main_to_data = defaultdict(lambda: {"afat_total": 0, "imp_total": 0})

    for member in corp_members:
        user_id = member.user_id
        main_character = member.main_character.character_name

        afat_total = (
            MonthlyUserStats.objects.filter(
                user_id=user_id, fleet_type__source="afat", month=month, year=year
            ).aggregate(total=Sum("total_fats"))["total"]
            or 0
        )

        imp_total = (
            MonthlyUserStats.objects.filter(
                user_id=user_id, fleet_type__source="imp", month=month, year=year
            ).aggregate(total=Sum("total_fats"))["total"]
            or 0
        )

        main_to_data[main_character]["afat_total"] += afat_total
        main_to_data[main_character]["imp_total"] += imp_total

        # Collect user data for top 5 calculations
        user_data.append(
            {
                "name": main_character,
                "afat_total": afat_total,
                "combined_total": afat_total + imp_total,
            }
        )

    corp_data = sorted(
        [
            {
                "name": main,
                "afat_total": data["afat_total"],
                "imp_total": data["imp_total"],
            }
            for main, data in main_to_data.items()
        ],
        key=lambda x: x["name"],
    )
    raw_data = corp_data

    context = {
        "bar_chart": bar_chart,
        "line_chart": line_chart,
        "raw_data": raw_data,
    }

    return render(request, "papstats/corporation_data.html", context)
