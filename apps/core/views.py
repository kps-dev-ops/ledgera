from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import SocieteMembership


@login_required
def activer_societe(request, pk):
    """Bascule la société active. Refuse (404) toute société non habilitée."""
    membership = get_object_or_404(SocieteMembership, user=request.user, societe_id=pk, actif=True)
    request.session["societe_id"] = membership.societe_id
    return redirect("dashboard")


@login_required
def aucune_societe(request):
    return render(request, "core/aucune_societe.html")
