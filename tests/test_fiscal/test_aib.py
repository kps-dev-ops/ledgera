from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.comptabilite.models import (
    CompteComptable,
    Exercice,
    Journal,
    LigneEcriture,
    Periode,
)
from apps.fiscal.models import ConfigurationAIB, DeclarationAIB
from apps.fiscal.selectors import declarations_aib_par_annee
from apps.fiscal.services import (
    comptabiliser_aib,
    creer_declaration_aib,
    generer_bordereau_aib_pdf,
)


class AIBTestBase(TenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.code = "TEST"
        tenant.raison_sociale = "Société de Test"
        tenant.pays = "BJ"
        tenant.devise = "XOF"
        tenant.referentiel = "SYSCOHADA"
        return tenant

    def setUp(self):
        super().setUp()
        with connection.cursor() as c:
            c.execute("SET LOCAL app.user_id = 1")
            c.execute("SET LOCAL app.user_email = 'test@ledgera.app'")
            c.execute("SET LOCAL app.ip = '127.0.0.1'")
        self.user = get_user_model().objects.create_user(username="t@x.fr", email="t@x.fr", password="x")
        self.c521 = CompteComptable.objects.create(numero="521000", libelle="Banque", classe=5)
        self.c449 = CompteComptable.objects.create(numero="449100", libelle="AIB - acompte IBS", classe=4)
        self.ex = Exercice.objects.create(code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31))
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.ex, mois=m)
        self.od = Journal.objects.create(code="OD", libelle="OD", type_journal="OD")
        self.config = ConfigurationAIB.objects.create(
            libelle="AIB Bénin 1%", taux=Decimal("1.00"),
            compte_aib=self.c449, compte_tresorerie=self.c521, journal=self.od,
        )


class TestCalculAIB(AIBTestBase):
    def test_montant(self):
        decl = creer_declaration_aib(self.config, 2026, 1, Decimal("1000000.00"), self.user)
        assert isinstance(decl, DeclarationAIB)
        assert decl.montant_aib == Decimal("10000.00")
        assert decl.statut == "BROUILLON"


class TestComptabilisationAIB(AIBTestBase):
    def test_comptabilise_equilibre(self):
        decl = creer_declaration_aib(self.config, 2026, 1, Decimal("1000000.00"), self.user)
        piece = comptabiliser_aib(decl, self.user)
        decl.refresh_from_db()
        assert decl.statut == "VALIDEE" and decl.piece_id == piece.id
        assert piece.statut == "VALIDEE" and piece.total_debit == piece.total_credit == Decimal("10000.00")
        assert LigneEcriture.objects.filter(piece=piece, compte=self.c449, debit=Decimal("10000.00")).exists()
        assert LigneEcriture.objects.filter(piece=piece, compte=self.c521, credit=Decimal("10000.00")).exists()

    def test_refuse_recomptabilisation(self):
        decl = creer_declaration_aib(self.config, 2026, 1, Decimal("1000000.00"), self.user)
        comptabiliser_aib(decl, self.user)
        with pytest.raises(ValueError):
            comptabiliser_aib(decl, self.user)


class TestBordereauEtHistoriqueAIB(AIBTestBase):
    def test_pdf_et_historique(self):
        decl = creer_declaration_aib(self.config, 2026, 1, Decimal("1000000.00"), self.user)
        assert len(declarations_aib_par_annee(2026)) == 1
        try:
            pdf = generer_bordereau_aib_pdf(decl)
        except OSError:
            pytest.skip("WeasyPrint/GTK indisponible")
        assert pdf[:4] == b"%PDF"


class TestCloisonnementAIB(AIBTestBase):
    def test_table_absente_du_public(self):
        from django_tenants.utils import schema_context

        creer_declaration_aib(self.config, 2026, 1, Decimal("1000000.00"), self.user)
        with schema_context("public"):
            with connection.cursor() as c:
                c.execute("SELECT to_regclass('public.fiscal_declarationaib')")
                assert c.fetchone()[0] is None
