"""Routes."""

# Django
from django.shortcuts import redirect
from django.urls import path

# Pap Stats
from papstats.views import alliance, corporation, fc, main

app_name: str = "papstats"

urlpatterns = [
    # alliance
    path("", lambda request: redirect("papstats:alliance"), name="index"),
    path("alliance/", alliance.alliance, name="alliance"),
    path(
        "alliance/<int:year>/",
        alliance.alliance,
        name="alliance",
    ),
    path(
        "alliance/<int:year>/<int:month>/",
        alliance.alliance,
        name="alliance",
    ),
    path(
        "data/alliance/<int:allyid>/<int:year>/<int:month>/",
        alliance.alliance_data,
        name="alliance_data",
    ),
    # corp
    path("corporation/", corporation.corporation, name="corporation"),
    path("corporation/<int:corpid>/", corporation.corporation, name="corporation"),
    path(
        "corporation/<int:corpid>/<int:year>/",
        corporation.corporation,
        name="corporation",
    ),
    path(
        "corporation/<int:corpid>/<int:year>/<int:month>/",
        corporation.corporation,
        name="corporation",
    ),
    path(
        "data/corporation/<int:corpid>/<int:year>/<int:month>/",
        corporation.corporation_data,
        name="corporation_data",
    ),
    # fc
    path("fc/", fc.fc, name="fc"),
    path(
        "fc/<int:year>/",
        fc.fc,
        name="fc",
    ),
    path(
        "fc/<int:year>/<int:month>/",
        fc.fc,
        name="fc",
    ),
    path(
        "data/fc/<int:year>/<int:month>/",
        fc.fc_data,
        name="fc_data",
    ),
    # admin
    path("admin/", main.admin, name="admin"),
    path("admin/upload", main.upload_data, name="csvupload"),
]
