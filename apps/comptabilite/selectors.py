from decimal import Decimal

from django.db.models import Q, Sum

from .models import CompteComptable, Exercice, LigneEcriture, PieceComptable


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


def apercu_cloture(exercice) -> dict:
    """Aperçu avant clôture : brouillards, résultat net, total à-nouveaux, N+1, cloturable."""
    nb_brouillards = PieceComptable.objects.filter(exercice=exercice, statut="BROUILLARD").count()

    gestion = (
        LigneEcriture.objects.filter(piece__exercice=exercice, piece__statut="VALIDEE")
        .values("compte__classe")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    produits = charges = Decimal("0.00")
    for g in gestion:
        d = g["d"] or Decimal("0.00")
        c = g["c"] or Decimal("0.00")
        if g["compte__classe"] == 7:
            produits += c - d
        elif g["compte__classe"] == 6:
            charges += d - c
    resultat_net = produits - charges

    bilan = (
        LigneEcriture.objects.filter(
            piece__exercice=exercice, piece__statut="VALIDEE", compte__classe__lte=5
        )
        .values("compte_id", "tiers_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    total_anouveaux = sum(
        (abs((b["d"] or Decimal("0.00")) - (b["c"] or Decimal("0.00"))) for b in bilan),
        Decimal("0.00"),
    )

    annee_suivante = exercice.date_fin.year + 1
    exercice_suivant_existe = Exercice.objects.filter(code=str(annee_suivante)).exists()

    return {
        "nb_brouillards": nb_brouillards,
        "resultat_net": resultat_net,
        "total_anouveaux": total_anouveaux,
        "exercice_suivant_existe": exercice_suivant_existe,
        "cloturable": exercice.statut != "CLOTURE" and nb_brouillards == 0,
    }
