from datetime import date
from decimal import Decimal

from apps.immobilisations.amortissement import plan_lineaire


def test_lineaire_total_egale_base_amortissable():
    # 12 000 sur 5 ans, mise en service au 1er janvier => 60 mensualités de 200
    lignes = plan_lineaire(Decimal("12000.00"), Decimal("0.00"), 5, date(2026, 1, 1))
    assert lignes[0].montant == Decimal("200.00")
    assert lignes[0].annee == 2026 and lignes[0].mois == 1
    total = sum((l.montant for l in lignes), Decimal("0.00"))
    assert total == Decimal("12000.00")
    assert lignes[-1].cumul == Decimal("12000.00")
    assert lignes[-1].vnc == Decimal("0.00")


def test_lineaire_respecte_valeur_residuelle():
    lignes = plan_lineaire(Decimal("12000.00"), Decimal("2000.00"), 5, date(2026, 1, 1))
    total = sum((l.montant for l in lignes), Decimal("0.00"))
    assert total == Decimal("10000.00")  # base = coût - valeur résiduelle
    assert lignes[-1].vnc == Decimal("2000.00")


def test_lineaire_prorata_premier_mois():
    # mise en service le 16 du mois => prorata (30-16+1)/30 = 15/30 = 0.5
    lignes = plan_lineaire(Decimal("12000.00"), Decimal("0.00"), 5, date(2026, 1, 16))
    assert lignes[0].montant == Decimal("100.00")  # 200 * 0.5
    total = sum((l.montant for l in lignes), Decimal("0.00"))
    assert total == Decimal("12000.00")  # le reliquat est soldé en fin de plan
