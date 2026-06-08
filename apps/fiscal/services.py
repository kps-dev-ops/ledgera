import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from .models import DeclarationTVA


def _bornes_periode(periodicite: str, annee: int, periode_num: int) -> tuple[date, date]:
    if periodicite == "TRIMESTRIELLE":
        mois_debut = (periode_num - 1) * 3 + 1
        mois_fin = mois_debut + 2
    else:
        mois_debut = mois_fin = periode_num
    debut = date(annee, mois_debut, 1)
    fin = date(annee, mois_fin, calendar.monthrange(annee, mois_fin)[1])
    return debut, fin


def _solde(comptes, date_debut, date_fin, sens: str) -> Decimal:
    from apps.comptabilite.models import LigneEcriture

    agg = LigneEcriture.objects.filter(
        compte__in=comptes, piece__statut="VALIDEE",
        piece__date_piece__gte=date_debut, piece__date_piece__lte=date_fin,
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    d = agg["d"] or Decimal("0.00")
    c = agg["c"] or Decimal("0.00")
    return (c - d) if sens == "CREDITEUR" else (d - c)


def calculer_tva(config, date_debut, date_fin) -> dict:
    """TVA collectée (créditeur) − déductible (débiteur) sur la période."""
    collectee = _solde(config.comptes_collectee.all(), date_debut, date_fin, "CREDITEUR")
    deductible = _solde(config.comptes_deductible.all(), date_debut, date_fin, "DEBITEUR")
    return {"tva_collectee": collectee, "tva_deductible": deductible, "tva_nette": collectee - deductible}


@transaction.atomic
def creer_declaration_tva(config, annee: int, periode_num: int, user) -> DeclarationTVA:
    debut, fin = _bornes_periode(config.periodicite, annee, periode_num)
    res = calculer_tva(config, debut, fin)
    decl, _ = DeclarationTVA.objects.get_or_create(
        configuration=config, annee=annee, periode_num=periode_num,
        defaults={"date_debut": debut, "date_fin": fin},
    )
    decl.date_debut, decl.date_fin = debut, fin
    decl.tva_collectee = res["tva_collectee"]
    decl.tva_deductible = res["tva_deductible"]
    decl.tva_nette = res["tva_nette"]
    decl.save()
    return decl
