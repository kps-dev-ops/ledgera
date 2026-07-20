from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.comptabilite.models import (
    CompteComptable,
    Exercice,
    Journal,
    LigneEcriture,
    Periode,
    PieceComptable,
)
from apps.comptabilite.models import LigneEcriture as _LE
from apps.comptabilite.services import valider_piece
from apps.fiscal.models import ConfigurationTVA, DeclarationTVA
from apps.fiscal.services import calculer_tva, comptabiliser_liquidation, creer_declaration_tva, generer_bordereau_pdf


class FiscalTestBase(TenantTestCase):
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
        self.c4431 = CompteComptable.objects.create(numero="443100", libelle="TVA collectée", classe=4)
        self.c4452 = CompteComptable.objects.create(numero="445200", libelle="TVA déductible", classe=4)
        self.c4441 = CompteComptable.objects.create(numero="444100", libelle="TVA due", classe=4)
        self.c4449 = CompteComptable.objects.create(numero="444900", libelle="Crédit de TVA", classe=4)
        self.c601 = CompteComptable.objects.create(numero="601000", libelle="Achats", classe=6)
        self.c701 = CompteComptable.objects.create(numero="701000", libelle="Ventes", classe=7)
        self.ex = Exercice.objects.create(code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31))
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.ex, mois=m)
        self.od = Journal.objects.create(code="OD", libelle="OD", type_journal="OD")
        self.config = ConfigurationTVA.objects.create(
            libelle="TVA Bénin", periodicite="MENSUELLE", compte_tva_due=self.c4441,
            compte_credit_tva=self.c4449, journal=self.od,
        )
        self.config.comptes_collectee.add(self.c4431)
        self.config.comptes_deductible.add(self.c4452)

    def _piece(self, lignes, date_piece=date(2026, 1, 15)):
        """lignes: list de (compte, debit, credit) en str. Crée et valide une pièce OD."""
        piece = PieceComptable.objects.create(
            journal=self.od, exercice=self.ex, date_piece=date_piece,
            libelle="Op", statut="BROUILLARD", auteur=self.user,
        )
        for i, (compte, d, c) in enumerate(lignes, start=1):
            LigneEcriture.objects.create(piece=piece, numero_ligne=i, compte=compte,
                                         debit=Decimal(d), credit=Decimal(c))
        return valider_piece(piece, self.user)


class TestCalculTVA(FiscalTestBase):
    def test_tva_a_payer(self):
        self._piece([(self.c521, "1200.00", "0.00"), (self.c701, "0.00", "1000.00"), (self.c4431, "0.00", "200.00")])
        self._piece([(self.c601, "500.00", "0.00"), (self.c4452, "100.00", "0.00"), (self.c521, "0.00", "600.00")])
        res = calculer_tva(self.config, date(2026, 1, 1), date(2026, 1, 31))
        assert res["tva_collectee"] == Decimal("200.00")
        assert res["tva_deductible"] == Decimal("100.00")
        assert res["tva_nette"] == Decimal("100.00")

    def test_credit_de_tva(self):
        self._piece([(self.c601, "500.00", "0.00"), (self.c4452, "300.00", "0.00"), (self.c521, "0.00", "800.00")])
        res = calculer_tva(self.config, date(2026, 1, 1), date(2026, 1, 31))
        assert res["tva_nette"] == Decimal("-300.00")


class TestCreerDeclaration(FiscalTestBase):
    def test_creer_declaration_mensuelle(self):
        self._piece([(self.c521, "1200.00", "0.00"), (self.c701, "0.00", "1000.00"), (self.c4431, "0.00", "200.00")])
        decl = creer_declaration_tva(self.config, 2026, 1, self.user)
        assert isinstance(decl, DeclarationTVA)
        assert decl.date_debut == date(2026, 1, 1) and decl.date_fin == date(2026, 1, 31)
        assert decl.tva_collectee == Decimal("200.00") and decl.tva_nette == Decimal("200.00")
        assert decl.statut == "BROUILLON"


class TestLiquidation(FiscalTestBase):
    def test_liquidation_equilibree_tva_a_payer(self):
        self._piece([(self.c521, "1200.00", "0.00"), (self.c701, "0.00", "1000.00"), (self.c4431, "0.00", "200.00")])
        self._piece([(self.c601, "500.00", "0.00"), (self.c4452, "100.00", "0.00"), (self.c521, "0.00", "600.00")])
        decl = creer_declaration_tva(self.config, 2026, 1, self.user)
        piece = comptabiliser_liquidation(decl, self.user)
        decl.refresh_from_db()
        assert decl.statut == "VALIDEE" and decl.piece_liquidation_id == piece.id
        assert piece.statut == "VALIDEE" and piece.total_debit == piece.total_credit
        assert _LE.objects.filter(piece=piece, compte=self.c4441, credit=Decimal("100.00")).exists()
        assert _LE.objects.filter(piece=piece, compte=self.c4431, debit=Decimal("200.00")).exists()
        assert _LE.objects.filter(piece=piece, compte=self.c4452, credit=Decimal("100.00")).exists()

    def test_refuse_reliquidation(self):
        import pytest
        self._piece([(self.c521, "1200.00", "0.00"), (self.c701, "0.00", "1000.00"), (self.c4431, "0.00", "200.00")])
        decl = creer_declaration_tva(self.config, 2026, 1, self.user)
        comptabiliser_liquidation(decl, self.user)
        with pytest.raises(ValueError):
            comptabiliser_liquidation(decl, self.user)


class TestBordereau(FiscalTestBase):
    def test_bordereau_pdf_non_vide(self):
        import pytest

        self._piece([(self.c521, "1200.00", "0.00"), (self.c701, "0.00", "1000.00"), (self.c4431, "0.00", "200.00")])
        decl = creer_declaration_tva(self.config, 2026, 1, self.user)
        try:
            pdf = generer_bordereau_pdf(decl)
        except OSError as exc:
            # Les libs natives de WeasyPrint (GTK : libgobject/pango/cairo) ne sont
            # pas installées sur cette machine. Le wrapper reste testé ailleurs sur
            # un environnement équipé ; ici on saute plutôt que de masquer le besoin.
            pytest.skip(f"WeasyPrint natif indisponible (GTK manquant) : {exc}")
        assert isinstance(pdf, (bytes, bytearray)) and pdf[:4] == b"%PDF"


class TestCloisonnement(FiscalTestBase):
    def test_table_declaration_absente_du_public(self):
        from django.db import connection
        from django_tenants.utils import schema_context

        creer_declaration_tva(self.config, 2026, 1, self.user)
        with schema_context("public"):
            with connection.cursor() as c:
                c.execute("SELECT to_regclass('public.fiscal_declarationtva')")
                assert c.fetchone()[0] is None
