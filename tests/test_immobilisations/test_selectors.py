from datetime import date
from decimal import Decimal

from apps.immobilisations.selectors import tableau_immobilisations
from apps.immobilisations.services import comptabiliser_dotations, generer_plan_amortissement
from tests.test_immobilisations.test_services import ImmoTestBase


class TestTableauImmobilisations(ImmoTestBase):
    def test_vnc_a_une_date(self):
        immo = self._immo()  # 12000 / 5 ans / linéaire => 200/mois
        generer_plan_amortissement(immo)
        for m in range(1, 7):  # comptabilise 6 mois => cumul 1200
            comptabiliser_dotations(self.exercice, m, self.user)
        lignes = tableau_immobilisations(date(2026, 6, 30))
        ligne = next(l for l in lignes if l["code"] == immo.code)
        assert ligne["cumul_amortissements"] == Decimal("1200.00")
        assert ligne["vnc"] == Decimal("10800.00")
