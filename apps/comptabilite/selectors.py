from django.db.models import Q

from .models import CompteComptable


def search_comptes(q: str, classe_filter: int | None = None, limit: int = 20):
    """Recherche de comptes : numero startswith q OR libelle icontains q."""
    if not q:
        return CompteComptable.objects.none()
    qs = CompteComptable.objects.filter(actif=True).filter(
        Q(numero__startswith=q) | Q(libelle__icontains=q)
    )
    if classe_filter is not None:
        qs = qs.filter(classe=classe_filter)
    return qs.order_by("numero")[:limit]


def search_tiers(q: str, type_tiers: str | None = None, limit: int = 20):
    """Recherche de tiers : code_auxiliaire startswith q OR raison_sociale icontains q."""
    from apps.tiers.models import Tiers

    if not q:
        return Tiers.objects.none()
    qs = Tiers.objects.filter(actif=True).filter(
        Q(code_auxiliaire__istartswith=q) | Q(raison_sociale__icontains=q)
    )
    if type_tiers:
        qs = qs.filter(type_tiers=type_tiers)
    return qs.order_by("raison_sociale")[:limit]
