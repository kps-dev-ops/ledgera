from decimal import Decimal

from django.db.models import Sum

from apps.comptabilite.models import LigneEcriture


def etat_rapprochement(releve) -> dict:
    """État de rapprochement : soldes, total pointé, lignes en attente, écritures
    comptables non pointées, écart théorique.
    """
    lignes = list(releve.lignes.all())
    pointees = [ligne for ligne in lignes if ligne.statut != "NON_POINTEE"]
    en_attente = [ligne for ligne in lignes if ligne.statut == "NON_POINTEE"]
    total_pointe = sum((ligne.montant for ligne in pointees), Decimal("0.00"))

    compte = releve.compte_bancaire.compte_comptable
    ecritures_non_pointees = list(
        LigneEcriture.objects.select_related("piece").filter(
            compte=compte, pointee=False, piece__statut="VALIDEE",
            piece__date_piece__gte=releve.date_debut, piece__date_piece__lte=releve.date_fin,
        )
    )
    soldes = LigneEcriture.objects.filter(
        compte=compte, piece__statut="VALIDEE", piece__date_piece__lte=releve.date_fin
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    solde_comptable = (soldes["d"] or Decimal("0.00")) - (soldes["c"] or Decimal("0.00"))

    return {
        "solde_initial": releve.solde_initial,
        "solde_final": releve.solde_final,
        "total_pointe": total_pointe,
        "lignes_en_attente": en_attente,
        "nb_en_attente": len(en_attente),
        "ecritures_non_pointees": ecritures_non_pointees,
        "solde_comptable": solde_comptable,
        "ecart": releve.solde_final - (releve.solde_initial + total_pointe),
    }
