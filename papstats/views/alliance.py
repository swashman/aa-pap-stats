"""Views."""

# flake8: noqa: E402
# Standard Library
import base64
import calendar
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
from django.core.exceptions import BadRequest, PermissionDenied
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

# Alliance Auth
from allianceauth.authentication.models import UserProfile
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger

# Pap Stats
from papstats.models import MonthlyCorpStats, MonthlyFleetType
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
def alliance(request: HttpRequest, year: int = None, month: int = None) -> HttpResponse:
    """Handles alliance-related views with optional parameters."""
    alliance_name = (
        request.user.profile.main_character.corporation.alliance.alliance_name
    )
    alliance_id = request.user.profile.main_character.corporation.alliance.alliance_id
    try:
        EveAllianceInfo.objects.get(alliance_id=alliance_id)
    except EveAllianceInfo.DoesNotExist:
        raise BadRequest()
    context = {
        "alliance": alliance_name,
        "alliance_id": alliance_id,
        **get_date_context(year, month),  # Adds all date-related values
        **get_navbar_elements(request.user),
    }
    return render(request, "papstats/alliance.html", context)


@login_required
def alliance_data(
    request: HttpRequest, allyid: int, year: int, month: int
) -> HttpResponse:
    """Generate alliance charts with fleet data grouped by main character's corporation."""

    if not request.headers.get("HX-Request"):
        raise PermissionDenied("No Direct Access!")

    month_name = calendar.month_name[month]
    try:
        all_corps = (
            EveCorporationInfo.objects.filter(alliance__alliance_id=allyid)
            .exclude(corporation_id__in=settings.STATS_IGNORE_CORPS)
            .order_by("corporation_ticker")
        )
        corp_names = list(all_corps.values_list("corporation_ticker", flat=True))
        stats = MonthlyCorpStats.objects.filter(
            month=month,
            year=year,
            corporation_id__in=all_corps.values_list("corporation_id", flat=True),
        ).select_related("fleet_type")
    except EveCorporationInfo.DoesNotExist:
        return render(
            request,
            "papstats/alliance_data.html",
            {"staterror": "Could not find corporations"},
        )
    except MonthlyCorpStats.DoesNotExist:
        return render(
            request,
            "papstats/alliance_data.html",
            {"staterror": "No stats for selected alliance or date"},
        )

    if stats.count() == 0:
        return render(
            request,
            "papstats/alliance_data.html",
            {"staterror": "No stats for selected alliance or date"},
        )

    fleet_types = MonthlyFleetType.objects.filter(month=month, year=year)
    logger.info(
        "Available Fleet Types: %s", list(fleet_types.values("id", "name", "source"))
    )

    logger.info(
        "All Corps IDs: %s", list(all_corps.values_list("corporation_id", flat=True))
    )
    logger.info("Stats Query Result: %s", list(stats))

    logger.info(
        "Stats Query Corporations (Full): %s",
        list(stats.values_list("corporation_id", flat=True)),
    )

    logger.info("Stats Query SQL: %s", str(stats.query))

    data_afat = {}
    for corp in corp_names:
        logger.info("Corp: %s", corp)
        data_afat[corp] = {
            ft.name: 0
            for ft in MonthlyFleetType.objects.filter(
                month=month, year=year, source="afat"
            )
        }
    data_imp = {
        corp: {
            ft.name: 0
            for ft in MonthlyFleetType.objects.filter(
                month=month, year=year, source="imp"
            )
        }
        for corp in corp_names
    }

    relative_data = {corp: {"AFAT": 0, "IMP": 0} for corp in corp_names}

    for stat in stats:
        logger.info(
            "Fleet Type Data - Corp: %s, Fleet Type: %s, Source: %s",
            stat.get_corporation().corporation_ticker,
            stat.fleet_type.name,
            stat.fleet_type.source,
        )
        corp_ticker = stat.get_corporation().corporation_ticker
        # total_mains = CorpStats.objects.get(corp=stat.get_corporation().pk).main_count
        corp_members = UserProfile.objects.filter(
            main_character__corporation_id=stat.get_corporation().corporation_id
        ).order_by("main_character__character_name")
        total_mains = corp_members.count()

        if stat.fleet_type.source == "afat":
            if corp_ticker in data_afat:  # Check if corp_ticker is in data_afat
                data_afat[corp_ticker][stat.fleet_type.name] += stat.total_fats
                if total_mains > 0:
                    relative_data[corp_ticker]["AFAT"] += stat.total_fats / total_mains
            else:
                logger.warning(
                    f"Ticker {corp_ticker} not found in data_afat, skipping stat."
                )

        elif stat.fleet_type.source == "imp":
            if corp_ticker in data_imp:  # Check if corp_ticker is in data_imp
                data_imp[corp_ticker][stat.fleet_type.name] += stat.total_fats
                if total_mains > 0:
                    relative_data[corp_ticker]["IMP"] += stat.total_fats / total_mains
            else:
                logger.warning(
                    f"Ticker {corp_ticker} not found in data_imp, skipping stat."
                )

    df_afat = pd.DataFrame(data_afat).T.fillna(0)
    df_imp = pd.DataFrame(data_imp).T.fillna(0)

    # Filter out columns with zero sums
    df_afat = df_afat.loc[:, (df_afat.sum(axis=0) != 0)]
    df_imp = df_imp.loc[:, (df_imp.sum(axis=0) != 0)]

    # Relative participation chart
    df_relative = pd.DataFrame(relative_data).T.fillna(0)

    x = np.arange(len(corp_names))

    # AFAT chart
    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    bottom_afat = np.zeros(len(corp_names))
    color_range_afat = plt.cm.viridis(np.linspace(0, 1, len(df_afat.columns)))

    for idx, column in enumerate(df_afat.columns):
        ax.bar(
            x,
            df_afat[column],
            bottom=bottom_afat,
            color=color_range_afat[idx],
            label=column,
        )
        bottom_afat += df_afat[column]

    for i, total in enumerate(bottom_afat):
        ax.text(
            i,
            total,
            f"{int(total)}",
            ha="center",
            va="bottom",
            color="white",
            fontsize=10,
        )

    ax.set_title(
        f"LAWN Fleet Breakdown for {month_name} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Fats", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    afat_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # IMP chart
    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    bottom_imp = np.zeros(len(corp_names))
    color_range_imp = plt.cm.winter(np.linspace(0, 1, len(df_imp.columns)))

    for idx, column in enumerate(df_imp.columns):
        ax.bar(
            x,
            df_imp[column],
            bottom=bottom_imp,
            color=color_range_imp[idx],
            label=column,
        )
        bottom_imp += df_imp[column]

    for i, total in enumerate(bottom_imp):
        ax.text(
            i,
            total,
            f"{int(total)}",
            ha="center",
            va="bottom",
            color="white",
            fontsize=10,
        )

    ax.set_title(
        f"IMPERIUM Fleet Breakdown for {month_name} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Paps", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    imp_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # Combined chart
    total_afat = df_afat.sum(axis=1)
    total_imp = df_imp.sum(axis=1)

    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)

    ax.bar(x - 0.2, total_afat, width=0.4, label="LAWN", color="cyan")
    ax.bar(x + 0.2, total_imp, width=0.4, label="IMP", color="blue")

    for i in range(len(corp_names)):
        ax.text(
            i - 0.2,
            total_afat.iloc[i],
            f"{int(total_afat.iloc[i])}",
            ha="center",
            va="bottom",
            color="white",
        )
        ax.text(
            i + 0.2,
            total_imp.iloc[i],
            f"{int(total_imp.iloc[i])}",
            ha="center",
            va="bottom",
            color="white",
        )

    ax.set_title(
        f"Fleet Participation for {month_name} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Fats", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    combined_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # Pie chart for AFAT fleet type proportions
    afat_totals = df_afat.sum(axis=0)
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    wedges, texts, autotexts = ax.pie(
        afat_totals,
        autopct=lambda p: f"{p:.1f}%" if p > 1 else "",
        startangle=140,
        colors=color_range_afat,
        pctdistance=0.85,  # Adjust this value to move the labels further out
    )
    plt.setp(texts, color="white")
    plt.setp(autotexts, color="black")  # Set autopct text color
    ax.set_title(
        f"Fleet Type Participation for {month_name} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.legend(
        wedges,
        afat_totals.index,
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        facecolor="#2c2f33",
        edgecolor="white",
        title_fontsize="13",
        fontsize="11",
        labelcolor="lightgray",
    )
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    pie_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    start_month = (month - months_to_display) % 12 or 12
    start_year = year if month > months_to_display else year - 1
    date_range = [
        (start_year + (start_month + i - 1) // 12, (start_month + i - 1) % 12 + 1)
        for i in range(months_to_display + 1)  # Include current month
    ]
    # Line chart for month over month AFAT data
    afat_stats = (
        MonthlyCorpStats.objects.filter(
            corporation_id__in=all_corps.values_list("corporation_id", flat=True),
            fleet_type__source="afat",
            year__in=[start_year, year],
            month__in=[date[1] for date in date_range],
        )
        .values("year", "month")
        .annotate(total=Sum("total_fats"))
        .order_by("year", "month")
    )

    date_totals = {date: 0 for date in date_range}
    for item in afat_stats:
        date_totals[(item["year"], item["month"])] = item["total"]

    dates = [
        datetime(year=year, month=month, day=1) for year, month in date_totals.keys()
    ]
    totals = list(date_totals.values())

    # Calculate the running average
    running_avg = pd.Series(totals).rolling(window=3, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.plot(dates, totals, marker="o", color="cyan", label="Total Fats")
    ax.plot(dates, running_avg, linestyle="--", color="orange", label="Running Average")
    # Annotate the total for each month

    for i, total in enumerate(totals):
        if total > 0:
            ax.text(
                dates[i],
                total + 5,
                f"{total}",
                ha="center",
                va="bottom",
                color="white",
                fontsize=10,
            )

    ax.set_title(
        "Month Over Month Lawn Fats", color="white", fontsize=16, fontweight="bold"
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
    plt.close(fig)

    # Relative participation chart
    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)

    bar_afat = ax.bar(
        x - 0.2, df_relative["AFAT"], width=0.4, label="LAWN", color="cyan"
    )
    bar_imp = ax.bar(x + 0.2, df_relative["IMP"], width=0.4, label="IMP", color="blue")

    for bar in bar_afat:
        yval = bar.get_height()
        if yval > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval,
                f"{yval:.1f}",
                ha="center",
                va="bottom",
                color="white",
            )

    for bar in bar_imp:
        yval = bar.get_height()
        if yval > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval,
                f"{yval:.1f}",
                ha="center",
                va="bottom",
                color="white",
            )

    ax.set_title(
        f"Relative Participation(Fleets/Main) for {month_name} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Relative Participation", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    relative_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    context = {
        "afat_chart": afat_chart,
        "imp_chart": imp_chart,
        "combined_chart": combined_chart,
        "pie_chart": pie_chart,
        "line_chart": line_chart,
        "relative_chart": relative_chart,
    }
    return render(request, "papstats/alliance_data.html", context)
