from datetime import date
from decimal import Decimal

from apps.immobilisations.amortissement import coefficient_degressif, plan_degressif, plan_lineaire


def test_lineaire_total_egale_base_amortissable():
    # 12 000 sur 5 ans, mise en service au 1er janvier => 60 mensualités de 200
    lignes = plan_lineaire(Decimal("12000.00"), Decimal("0.00"), 5, date(2026, 1, 1))
    assert lignes[0].montant == Decimal("200.00")
    assert lignes[0].annee == 2026 and lignes[0].mois == 1
    total = sum((x.montant for x in lignes), Decimal("0.00"))
    assert total == Decimal("12000.00")
    assert lignes[-1].cumul == Decimal("12000.00")
    assert lignes[-1].vnc == Decimal("0.00")


def test_lineaire_respecte_valeur_residuelle():
    lignes = plan_lineaire(Decimal("12000.00"), Decimal("2000.00"), 5, date(2026, 1, 1))
    total = sum((x.montant for x in lignes), Decimal("0.00"))
    assert total == Decimal("10000.00")  # base = coût - valeur résiduelle
    assert lignes[-1].vnc == Decimal("2000.00")


def test_lineaire_prorata_premier_mois():
    # mise en service le 16 du mois => prorata (30-16+1)/30 = 15/30 = 0.5
    lignes = plan_lineaire(Decimal("12000.00"), Decimal("0.00"), 5, date(2026, 1, 16))
    assert lignes[0].montant == Decimal("100.00")  # 200 * 0.5
    total = sum((x.montant for x in lignes), Decimal("0.00"))
    assert total == Decimal("12000.00")  # le reliquat est soldé en fin de plan


def test_coefficient_degressif_par_duree():
    assert coefficient_degressif(3) == Decimal("1.25")
    assert coefficient_degressif(5) == Decimal("1.75")
    assert coefficient_degressif(8) == Decimal("2.25")


def test_degressif_total_egale_base_et_solde_a_zero():
    lignes = plan_degressif(Decimal("100000.00"), Decimal("0.00"), 5, date(2026, 1, 1))
    total = sum((x.montant for x in lignes), Decimal("0.00"))
    assert total == Decimal("100000.00")
    assert lignes[-1].cumul == Decimal("100000.00")
    assert lignes[-1].vnc == Decimal("0.00")


def test_degressif_premiere_annuite_superieure_au_lineaire():
    # taux dégressif 5 ans = (1/5)*1.75 = 0.35 ; 1ère annuité 35 000 > linéaire 20 000
    lignes = plan_degressif(Decimal("100000.00"), Decimal("0.00"), 5, date(2026, 1, 1))
    annuite_2026 = sum((x.montant for x in lignes if x.annee == 2026), Decimal("0.00"))
    assert annuite_2026 == Decimal("35000.00")


def test_degressif_bascule_en_lineaire_en_fin_de_plan():
    lignes = plan_degressif(Decimal("100000.00"), Decimal("0.00"), 5, date(2026, 1, 1))
    par_an = {}
    for x in lignes:
        par_an[x.annee] = par_an.get(x.annee, Decimal("0.00")) + x.montant
    annees = sorted(par_an)
    assert par_an[annees[-1]] == par_an[annees[-2]]  # deux dernières annuités égales
