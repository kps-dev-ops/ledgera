"""Calcul du bilan SYSCOHADA Révisé 2017 — version simplifiée V1.

V1 : valeur nette uniquement (les amortissements arriveront en L3 avec les
immobilisations). Mapping postes-clés couvrant l'essentiel d'un bilan PME.
"""
from decimal import Decimal

from django.db.models import F, Sum

from apps.comptabilite.models import LigneEcriture

# Postes ACTIF : (code, libellé, liste de préfixes de comptes)
BILAN_ACTIF = [
    # Actif immobilisé
    ("AE", "Charges immobilisées", ["20"]),
    ("AF", "Immobilisations incorporelles", ["21"]),
    ("AI", "Immobilisations corporelles", ["22", "23", "24"]),
    ("AN", "Immobilisations financières", ["26", "27"]),
    # Actif circulant
    ("BA", "Stocks et en-cours", ["31", "32", "33", "34", "35", "36", "37", "38"]),
    ("BB", "Créances clients", ["41"]),
    ("BI", "Autres créances", ["42", "43", "44", "45", "46", "47"]),
    # Trésorerie
    ("BQ", "Banques, chèques postaux", ["52", "53"]),
    ("BR", "Caisse", ["57"]),
]

# Postes PASSIF
BILAN_PASSIF = [
    # Capitaux propres
    ("CA", "Capital", ["10"]),
    ("CD", "Réserves", ["11", "12"]),
    ("CG", "Résultat net (variation)", ["13"]),  # Calculé spécialement
    ("CL", "Subventions / provisions réglementées", ["14", "15"]),
    # Dettes financières
    ("DA", "Emprunts et dettes financières", ["16", "17", "18"]),
    ("DC", "Provisions pour risques et charges", ["19"]),
    # Passif circulant
    ("DJ", "Fournisseurs", ["40"]),
    ("DM", "Dettes fiscales et sociales", ["42", "43", "44"]),
    ("DN", "Autres dettes", ["46", "47"]),
]


def _solde_par_prefixes(exercice, prefixes: list[str]) -> Decimal:
    """Somme du solde (debit - credit) des comptes commençant par un préfixe."""
    from django.db.models import Q

    cond = Q()
    for p in prefixes:
        cond |= Q(compte__numero__startswith=p)
    qs = LigneEcriture.objects.filter(
        piece__exercice=exercice, piece__statut="VALIDEE"
    ).filter(cond)
    agg = qs.aggregate(s=Sum(F("debit") - F("credit")))
    return agg["s"] or Decimal("0.00")


def _resultat_net(exercice) -> Decimal:
    """Résultat net = produits (cl. 7) - charges (cl. 6)."""
    qs = LigneEcriture.objects.filter(piece__exercice=exercice, piece__statut="VALIDEE")
    produits = qs.filter(compte__classe=7).aggregate(s=Sum(F("credit") - F("debit")))["s"] or Decimal("0.00")
    charges = qs.filter(compte__classe=6).aggregate(s=Sum(F("debit") - F("credit")))["s"] or Decimal("0.00")
    return produits - charges


def compute_bilan(exercice) -> dict:
    """Construit le bilan : actif (soldes débiteurs), passif (soldes créditeurs).

    Convention : un actif normal a solde > 0 (débiteur), un passif normal a
    solde < 0 (créditeur). On présente les valeurs absolues côté passif.
    """
    actif = []
    total_actif = Decimal("0.00")
    for code, libelle, prefixes in BILAN_ACTIF:
        montant = _solde_par_prefixes(exercice, prefixes)
        if montant != 0:
            actif.append({"code": code, "libelle": libelle, "montant": montant})
            total_actif += montant

    passif = []
    total_passif = Decimal("0.00")
    for code, libelle, prefixes in BILAN_PASSIF:
        if code == "CG":
            montant = _resultat_net(exercice)
        else:
            montant = -_solde_par_prefixes(exercice, prefixes)  # inverse pour passif
        if montant != 0:
            passif.append({"code": code, "libelle": libelle, "montant": montant})
            total_passif += montant

    return {
        "exercice": exercice,
        "actif": actif,
        "passif": passif,
        "total_actif": total_actif,
        "total_passif": total_passif,
        "equilibre": total_actif == total_passif,
        "ecart": total_actif - total_passif,
    }
