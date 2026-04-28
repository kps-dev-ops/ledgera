"""Calcul du compte de résultat SYSCOHADA Révisé 2017 — version simplifiée V1."""
from decimal import Decimal

from django.db.models import F, Q, Sum

from apps.comptabilite.models import LigneEcriture

# Produits (classe 7) — solde créditeur normal
PRODUITS = [
    ("TA", "Ventes de marchandises", ["701"]),
    ("TB", "Ventes de produits fabriqués", ["702", "703", "704"]),
    ("TC", "Travaux, services vendus", ["705", "706"]),
    ("TD", "Produits accessoires", ["707", "708"]),
    ("TI", "Subventions d'exploitation", ["71"]),
    ("TJ", "Autres produits d'exploitation", ["75", "78"]),
    ("TK", "Reprises de provisions, amortissements", ["79"]),
    ("TL", "Produits financiers", ["77"]),
    ("TN", "Produits HAO", ["82", "84", "86", "88"]),
]

# Charges (classe 6) — solde débiteur normal
CHARGES = [
    ("RA", "Achats de marchandises", ["601"]),
    ("RB", "Achats matières premières", ["602"]),
    ("RC", "Autres achats", ["604", "605", "608"]),
    ("RD", "Variations de stocks", ["603"]),
    ("RE", "Transports", ["61"]),
    ("RF", "Services extérieurs", ["62", "63"]),
    ("RG", "Impôts et taxes", ["64"]),
    ("RH", "Autres charges", ["65"]),
    ("RI", "Charges de personnel", ["66"]),
    ("RJ", "Frais financiers", ["67"]),
    ("RK", "Dotations aux amortissements et provisions", ["68"]),
    ("RL", "Charges HAO", ["81", "83", "85", "87"]),
    ("RM", "Impôts sur le résultat", ["89"]),
]


def _agg(exercice, prefixes: list[str], sens: str) -> Decimal:
    cond = Q()
    for p in prefixes:
        cond |= Q(compte__numero__startswith=p)
    qs = LigneEcriture.objects.filter(
        piece__exercice=exercice, piece__statut="VALIDEE"
    ).filter(cond)
    if sens == "credit":
        agg = qs.aggregate(s=Sum(F("credit") - F("debit")))
    else:
        agg = qs.aggregate(s=Sum(F("debit") - F("credit")))
    return agg["s"] or Decimal("0.00")


def compute_compte_resultat(exercice) -> dict:
    produits_lignes = []
    total_produits = Decimal("0.00")
    for code, libelle, prefixes in PRODUITS:
        m = _agg(exercice, prefixes, "credit")
        if m != 0:
            produits_lignes.append({"code": code, "libelle": libelle, "montant": m})
            total_produits += m

    charges_lignes = []
    total_charges = Decimal("0.00")
    for code, libelle, prefixes in CHARGES:
        m = _agg(exercice, prefixes, "debit")
        if m != 0:
            charges_lignes.append({"code": code, "libelle": libelle, "montant": m})
            total_charges += m

    resultat_net = total_produits - total_charges

    return {
        "exercice": exercice,
        "produits": produits_lignes,
        "charges": charges_lignes,
        "total_produits": total_produits,
        "total_charges": total_charges,
        "resultat_net": resultat_net,
    }
