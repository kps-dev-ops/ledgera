from datetime import date
from decimal import Decimal

from apps.banque.matching import choisir_ecriture, montant_concorde


def test_montant_concorde_encaissement_sur_debit():
    assert montant_concorde(Decimal("100.00"), Decimal("100.00"), Decimal("0.00")) is True
    assert montant_concorde(Decimal("100.00"), Decimal("0.00"), Decimal("100.00")) is False


def test_montant_concorde_decaissement_sur_credit():
    assert montant_concorde(Decimal("-100.00"), Decimal("0.00"), Decimal("100.00")) is True
    assert montant_concorde(Decimal("-100.00"), Decimal("100.00"), Decimal("0.00")) is False


def _cand(id, debit="0.00", credit="0.00", d=(2026, 1, 10), libelle=""):
    return {"id": id, "debit": Decimal(debit), "credit": Decimal(credit), "date": date(*d), "libelle": libelle}


def test_choisir_un_seul_candidat():
    cands = [_cand(1, debit="100.00", d=(2026, 1, 11))]
    assert choisir_ecriture(Decimal("100.00"), date(2026, 1, 10), "VIR SALAIRE", cands) == 1


def test_choisir_aucun_candidat_si_hors_fenetre():
    cands = [_cand(1, debit="100.00", d=(2026, 2, 1))]  # >5 jours
    assert choisir_ecriture(Decimal("100.00"), date(2026, 1, 10), "X", cands) is None


def test_choisir_depart_fuzzy_si_plusieurs():
    cands = [
        _cand(1, debit="100.00", d=(2026, 1, 10), libelle="VIREMENT LOYER MARS"),
        _cand(2, debit="100.00", d=(2026, 1, 10), libelle="ACHAT FOURNITURES"),
    ]
    assert choisir_ecriture(Decimal("100.00"), date(2026, 1, 10), "VIREMENT LOYER", cands) == 1


def test_choisir_none_si_ambigu():
    cands = [
        _cand(1, debit="100.00", d=(2026, 1, 10), libelle="PAIEMENT"),
        _cand(2, debit="100.00", d=(2026, 1, 10), libelle="PAIEMENT"),
    ]
    assert choisir_ecriture(Decimal("100.00"), date(2026, 1, 10), "PAIEMENT", cands) is None
