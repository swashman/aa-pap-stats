"""Routes."""

# Django
from django.urls import path

from . import views

app_name: str = "papstats"

urlpatterns = [
    path("", views.index, name="index"),
]
