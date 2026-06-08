from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LigneDotation:
    annee: int
    mois: int
    montant: Decimal
    cumul: Decimal
    vnc: Decimal


def _avancer(annee: int, mois: int) -> tuple[int, int]:
    return (annee + 1, 1) if mois == 12 else (annee, mois + 1)


def plan_lineaire(
    cout: Decimal, valeur_residuelle: Decimal, duree: int, date_mise_service: date
) -> list[LigneDotation]:
    """Plan linéaire mensuel, prorata du 1er mois (base 30 jours).

    Le reliquat dû au prorata est soldé sur une période supplémentaire en fin de
    plan. La dernière dotation est ajustée pour solder exactement la base.
    """
    base = cout - valeur_residuelle
    mensualite = _q(base / (duree * 12))
    facteur_premier = Decimal(30 - date_mise_service.day + 1) / Decimal(30)

    lignes: list[LigneDotation] = []
    cumul = Decimal("0.00")
    annee, mois = date_mise_service.year, date_mise_service.month
    premier = True
    while cumul < base:
        montant = _q(mensualite * facteur_premier) if premier else mensualite
        premier = False
        if cumul + montant > base:
            montant = base - cumul
        cumul += montant
        lignes.append(LigneDotation(annee, mois, montant, cumul, cout - cumul))
        annee, mois = _avancer(annee, mois)
    return lignes
