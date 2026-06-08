from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher

SEUIL_SIMILARITE = 0.6


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def montant_concorde(montant_releve: Decimal, debit: Decimal, credit: Decimal) -> bool:
    """Encaissement (montant>0) ↔ débit ; décaissement (montant<0) ↔ crédit."""
    if montant_releve > 0:
        return debit == montant_releve
    return credit == -montant_releve


def choisir_ecriture(
    montant: Decimal, date_op: date, libelle: str, candidats: list[dict], fenetre_jours: int = 5
) -> int | None:
    """Retourne l'id du candidat à pointer, ou None si aucun / ambigu.

    candidats : list de dict(id, debit, credit, date, libelle).
    Règle : montant concordant (signe) + date dans ±fenetre_jours. Si plusieurs,
    départage par similarité de libellé (ratio max ≥ SEUIL et strictement > au 2e).
    """
    eligibles = [
        c for c in candidats
        if montant_concorde(montant, c["debit"], c["credit"])
        and abs((c["date"] - date_op).days) <= fenetre_jours
    ]
    if not eligibles:
        return None
    if len(eligibles) == 1:
        return eligibles[0]["id"]
    scored = sorted(eligibles, key=lambda c: _similar(libelle, c["libelle"]), reverse=True)
    s_best = _similar(libelle, scored[0]["libelle"])
    s_second = _similar(libelle, scored[1]["libelle"])
    if s_best >= SEUIL_SIMILARITE and s_best > s_second:
        return scored[0]["id"]
    return None
