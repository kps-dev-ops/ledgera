import pytest
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
from apps.comptabilite.services import valider_piece
from apps.fiscal.models import ConfigurationIS, DeclarationIS
from apps.fiscal.selectors import declarations_is_par_exercice
from apps.fiscal.services import (
    ajouter_retraitement,
    comptabiliser_impot,
    creer_declaration_is,
    generer_bordereau_is_pdf,
    resultat_comptable,
)
from apps.comptabilite.models import LigneEcriture as _LE


class ISTestBase(TenantTestCase):
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
        self.c601 = CompteComptable.objects.create(numero="601000", libelle="Achats", classe=6)
        self.c701 = CompteComptable.objects.create(numero="701000", libelle="Ventes", classe=7)
        self.c891 = CompteComptable.objects.create(numero="891000", libelle="Impôt sur bénéfices", classe=8)
        self.c441 = CompteComptable.objects.create(numero="441000", libelle="État, IS", classe=4)
        self.ex = Exercice.objects.create(code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31))
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.ex, mois=m)
        self.od = Journal.objects.create(code="OD", libelle="OD", type_journal="OD")
        self.config = ConfigurationIS.objects.create(
            libelle="IBS Bénin", taux=Decimal("30.00"),
            compte_charge_impot=self.c891, compte_dette_impot=self.c441, journal=self.od,
        )

    def _piece(self, lignes, date_piece=date(2026, 6, 1)):
        piece = PieceComptable.objects.create(
            journal=self.od, exercice=self.ex, date_piece=date_piece,
            libelle="Op", statut="BROUILLARD", auteur=self.user,
        )
        for i, (compte, d, c) in enumerate(lignes, start=1):
            LigneEcriture.objects.create(piece=piece, numero_ligne=i, compte=compte, debit=Decimal(d), credit=Decimal(c))
        return valider_piece(piece, self.user)

    def _benefice(self, produits, charges):
        self._piece([(self.c521, str(produits), "0.00"), (self.c701, "0.00", str(produits))])
        self._piece([(self.c601, str(charges), "0.00"), (self.c521, "0.00", str(charges))])


class TestResultatComptable(ISTestBase):
    def test_resultat(self):
        self._benefice(10000, 6000)
        assert resultat_comptable(self.ex) == Decimal("4000.00")


class TestDeclarationIS(ISTestBase):
    def test_creer_et_retraitements(self):
        self._benefice(10000, 6000)
        decl = creer_declaration_is(self.config, self.ex, self.user)
        assert decl.resultat_comptable == Decimal("4000.00")
        assert decl.resultat_fiscal == Decimal("4000.00")
        assert decl.impot == Decimal("1200.00")
        ajouter_retraitement(decl, "Amende", Decimal("1000.00"), "REINTEGRATION")
        decl.refresh_from_db()
        assert decl.total_reintegrations == Decimal("1000.00")
        assert decl.resultat_fiscal == Decimal("5000.00")
        assert decl.impot == Decimal("1500.00")
        ajouter_retraitement(decl, "Plus-value exonérée", Decimal("2000.00"), "DEDUCTION")
        decl.refresh_from_db()
        assert decl.resultat_fiscal == Decimal("3000.00")
        assert decl.impot == Decimal("900.00")

    def test_deficit_impot_nul(self):
        self._benefice(5000, 8000)
        decl = creer_declaration_is(self.config, self.ex, self.user)
        assert decl.resultat_fiscal == Decimal("-3000.00")
        assert decl.impot == Decimal("0.00")


class TestComptabilisationIS(ISTestBase):
    def test_comptabilise_impot_equilibre(self):
        self._benefice(10000, 6000)
        decl = creer_declaration_is(self.config, self.ex, self.user)
        piece = comptabiliser_impot(decl, self.user)
        decl.refresh_from_db()
        assert decl.statut == "VALIDEE" and decl.piece_imposition_id == piece.id
        assert piece.statut == "VALIDEE" and piece.total_debit == piece.total_credit == Decimal("1200.00")
        assert _LE.objects.filter(piece=piece, compte=self.c891, debit=Decimal("1200.00")).exists()
        assert _LE.objects.filter(piece=piece, compte=self.c441, credit=Decimal("1200.00")).exists()

    def test_deficit_pas_de_piece_mais_validee(self):
        self._benefice(5000, 8000)
        decl = creer_declaration_is(self.config, self.ex, self.user)
        piece = comptabiliser_impot(decl, self.user)
        decl.refresh_from_db()
        assert piece is None and decl.statut == "VALIDEE"

    def test_refuse_recomptabilisation(self):
        self._benefice(10000, 6000)
        decl = creer_declaration_is(self.config, self.ex, self.user)
        comptabiliser_impot(decl, self.user)
        with pytest.raises(ValueError):
            comptabiliser_impot(decl, self.user)


class TestBordereauIS(ISTestBase):
    def test_pdf_non_vide(self):
        self._benefice(10000, 6000)
        decl = creer_declaration_is(self.config, self.ex, self.user)
        try:
            pdf = generer_bordereau_is_pdf(decl)
        except OSError:
            pytest.skip("WeasyPrint/GTK indisponible")
        assert pdf[:4] == b"%PDF"


class TestHistoriqueIS(ISTestBase):
    def test_historique(self):
        self._benefice(10000, 6000)
        creer_declaration_is(self.config, self.ex, self.user)
        assert len(declarations_is_par_exercice(self.ex)) == 1


class TestCloisonnementIS(ISTestBase):
    def test_table_absente_du_public(self):
        from django.db import connection
        from django_tenants.utils import schema_context

        self._benefice(10000, 6000)
        creer_declaration_is(self.config, self.ex, self.user)
        with schema_context("public"):
            with connection.cursor() as c:
                c.execute("SELECT to_regclass('public.fiscal_declarationis')")
                assert c.fetchone()[0] is None
