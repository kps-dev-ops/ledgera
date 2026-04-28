"""Centralisation des requêtes de lecture comptable.

Toutes les fonctions filtrent automatiquement sur statut=VALIDEE pour les
pièces (l'état comptable n'inclut jamais les brouillards).
"""
from decimal import Decimal

from django.db.models import F, Sum

from apps.comptabilite.models import LigneEcriture, PieceComptable


def _base_qs(exercice, date_debut=None, date_fin=None):
    qs = LigneEcriture.objects.filter(
        piece__exercice=exercice, piece__statut="VALIDEE"
    )
    if date_debut:
        qs = qs.filter(piece__date_piece__gte=date_debut)
    if date_fin:
        qs = qs.filter(piece__date_piece__lte=date_fin)
    return qs


def balance(exercice, date_debut=None, date_fin=None, classes=None):
    """Balance générale : agrégat par compte avec totaux et solde.

    Retourne un queryset itérable de dicts contenant :
    compte__numero, compte__libelle, compte__classe, compte__sens,
    total_debit, total_credit, solde.
    """
    qs = _base_qs(exercice, date_debut, date_fin)
    if classes:
        qs = qs.filter(compte__classe__in=classes)
    return (
        qs.values("compte__numero", "compte__libelle", "compte__classe", "compte__sens")
        .annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
            solde=Sum(F("debit") - F("credit")),
        )
        .order_by("compte__numero")
    )


def grand_livre_compte(compte, exercice, date_debut=None, date_fin=None, tiers=None):
    """Lignes détaillées d'un compte avec calcul du solde progressif.

    Retourne une liste de dicts (pas un queryset) car le solde progressif
    n'est pas calculable en SQL portable. Préfère une boucle Python.
    """
    qs = _base_qs(exercice, date_debut, date_fin).filter(compte=compte)
    if tiers:
        qs = qs.filter(tiers=tiers)
    qs = qs.select_related("piece", "piece__journal", "tiers").order_by(
        "piece__date_piece", "piece__numero", "numero_ligne"
    )

    result = []
    solde = Decimal("0.00")
    for ligne in qs:
        solde += (ligne.debit or Decimal("0.00")) - (ligne.credit or Decimal("0.00"))
        result.append({
            "ligne": ligne,
            "date": ligne.piece.date_piece,
            "journal": ligne.piece.journal.code,
            "piece_numero": ligne.piece.numero,
            "libelle": ligne.libelle or ligne.piece.libelle,
            "tiers": ligne.tiers,
            "debit": ligne.debit,
            "credit": ligne.credit,
            "solde": solde,
            "lettre": ligne.lettre_lettrage,
        })
    return result


def journal(journal_obj, exercice, date_debut=None, date_fin=None):
    """Pièces d'un journal sur la période, avec lignes détaillées prefetched."""
    qs = (
        PieceComptable.objects.filter(
            journal=journal_obj, exercice=exercice, statut="VALIDEE"
        )
        .prefetch_related("lignes__compte", "lignes__tiers")
        .order_by("date_piece", "numero")
    )
    if date_debut:
        qs = qs.filter(date_piece__gte=date_debut)
    if date_fin:
        qs = qs.filter(date_piece__lte=date_fin)
    return qs


def balance_auxiliaire(compte_collectif, exercice, date_debut=None, date_fin=None):
    """Balance auxiliaire : agrégat par tiers d'un compte collectif."""
    if not compte_collectif.collectif_tiers:
        raise ValueError(f"Compte {compte_collectif.numero} n'est pas collectif")
    qs = _base_qs(exercice, date_debut, date_fin).filter(compte=compte_collectif)
    return (
        qs.values("tiers__id", "tiers__code_auxiliaire", "tiers__raison_sociale")
        .annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
            solde=Sum(F("debit") - F("credit")),
        )
        .order_by("tiers__code_auxiliaire")
    )


def comptes_mouvementes(exercice, date_debut=None, date_fin=None):
    """Liste des comptes ayant au moins un mouvement (pour grand livre général)."""
    qs = _base_qs(exercice, date_debut, date_fin)
    return (
        qs.values("compte__id", "compte__numero", "compte__libelle", "compte__classe")
        .annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
            solde=Sum(F("debit") - F("credit")),
        )
        .order_by("compte__numero")
    )


def comptes_collectifs_avec_tiers(exercice):
    """Liste des comptes collectifs ayant des écritures (pour balance auxiliaire)."""
    from apps.comptabilite.models import CompteComptable

    ids = (
        _base_qs(exercice)
        .filter(compte__collectif_tiers=True)
        .values_list("compte_id", flat=True)
        .distinct()
    )
    return CompteComptable.objects.filter(id__in=ids).order_by("numero")
