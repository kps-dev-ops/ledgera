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


def coefficient_degressif(duree: int) -> Decimal:
    """Coefficient fiscal français (paramétrable). 3–4 ans : 1,25 ; 5–6 : 1,75 ; >6 : 2,25."""
    if duree <= 4:
        return Decimal("1.25")
    if duree <= 6:
        return Decimal("1.75")
    return Decimal("2.25")


def plan_degressif(
    cout: Decimal, valeur_residuelle: Decimal, duree: int, date_mise_service: date
) -> list[LigneDotation]:
    """Plan dégressif annuel (réparti mensuellement), bascule en linéaire.

    Chaque année : annuité = max(dégressif sur VNC, linéaire sur durée résiduelle).
    Prorata de la 1re année en mois entiers à compter du mois d'acquisition.
    """
    base = cout - valeur_residuelle
    taux_deg = (Decimal(1) / Decimal(duree)) * coefficient_degressif(duree)

    lignes: list[LigneDotation] = []
    cumul = Decimal("0.00")
    annee = date_mise_service.year
    mois_debut = date_mise_service.month
    annees_restantes = duree
    premiere = True
    while cumul < base and annees_restantes > 0:
        vnc_debut = base - cumul
        annuite = max(vnc_debut * taux_deg, vnc_debut / Decimal(annees_restantes))
        if premiere:
            annuite = annuite * Decimal(12 - mois_debut + 1) / Decimal(12)
        annuite = _q(annuite)
        if cumul + annuite > base:
            annuite = base - cumul

        mois_liste = list(range(mois_debut if premiere else 1, 13))
        mensualite = _q(annuite / len(mois_liste))
        cumul_annee = Decimal("0.00")
        for i, m in enumerate(mois_liste):
            montant = mensualite if i < len(mois_liste) - 1 else annuite - cumul_annee
            cumul_annee += montant
            cumul += montant
            lignes.append(LigneDotation(annee, m, montant, cumul, cout - cumul))

        annee += 1
        annees_restantes -= 1
        premiere = False
    # solde d'arrondi éventuel sur la dernière ligne
    if cumul < base and lignes:
        reliquat = base - cumul
        derniere = lignes[-1]
        lignes[-1] = LigneDotation(
            derniere.annee, derniere.mois, derniere.montant + reliquat, base, cout - base
        )
    return lignes


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
