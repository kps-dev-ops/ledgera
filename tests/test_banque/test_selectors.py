from datetime import date
from decimal import Decimal

from apps.banque.selectors import etat_rapprochement
from apps.banque.services import pointer_automatiquement
from tests.test_banque.test_services import BanqueTestBase


class TestEtatRapprochement(BanqueTestBase):
    def test_ecart_nul_quand_tout_pointe(self):
        self._ecriture_banque(Decimal("500.00"), "D", date(2026, 1, 10), "VIR CLIENT")
        releve = self._releve(
            [{"date_operation": date(2026, 1, 10), "libelle": "VIR CLIENT", "montant": Decimal("500.00")}],
            solde_initial=Decimal("0.00"), solde_final=Decimal("500.00"),
        )
        pointer_automatiquement(releve)
        etat = etat_rapprochement(releve)
        assert etat["total_pointe"] == Decimal("500.00")
        assert etat["nb_en_attente"] == 0
        assert etat["ecart"] == Decimal("0.00")
