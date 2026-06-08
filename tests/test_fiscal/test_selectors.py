from apps.fiscal.selectors import obligations_tva
from apps.fiscal.services import creer_declaration_tva
from tests.test_fiscal.test_services import FiscalTestBase


class TestObligations(FiscalTestBase):
    def test_obligations_mensuelles(self):
        creer_declaration_tva(self.config, 2026, 1, self.user)
        obls = obligations_tva(self.config, 2026)
        assert len(obls) == 12  # 12 mois
        jan = next(o for o in obls if o["periode_num"] == 1)
        assert jan["declaree"] is True
        fev = next(o for o in obls if o["periode_num"] == 2)
        assert fev["declaree"] is False
