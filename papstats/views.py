"""Views."""

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render


@login_required
@permission_required("papstats.basic_access")
def index(request):
    """Render index view."""
    context = {"text": "Hello, World!"}
    return render(request, "papstats/index.html", context)
