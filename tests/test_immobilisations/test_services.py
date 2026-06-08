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
from apps.immobilisations.models import CategorieImmobilisation, Dotation, Immobilisation
from apps.immobilisations.services import comptabiliser_dotations, generer_plan_amortissement, next_code_immobilisation


class ImmoTestBase(TenantTestCase):
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
        self.user = get_user_model().objects.create_user(
            username="t@x.fr", email="t@x.fr", password="x"
        )
        # Plan de comptes minimal pour les immobilisations
        self.c2441 = CompteComptable.objects.create(numero="244100", libelle="Matériel", classe=2)
        self.c2844 = CompteComptable.objects.create(numero="284410", libelle="Amort. matériel", classe=2)
        self.c6813 = CompteComptable.objects.create(numero="681300", libelle="Dotations", classe=6)
        self.c654 = CompteComptable.objects.create(numero="654000", libelle="VC cessions immo", classe=6)
        self.c754 = CompteComptable.objects.create(numero="754000", libelle="Produits cessions", classe=7)
        self.c485 = CompteComptable.objects.create(numero="485000", libelle="Créances cessions", classe=4)
        self.categorie = CategorieImmobilisation.objects.create(
            code="MAT", libelle="Matériel", compte_immo=self.c2441,
            compte_amortissement=self.c2844, compte_dotation=self.c6813,
            duree_defaut=5, mode_defaut="LINEAIRE",
        )
        # Exercice + périodes + journal OD
        self.exercice = Exercice.objects.create(
            code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31)
        )
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.exercice, mois=m)
        self.od = Journal.objects.create(code="OD", libelle="OD", type_journal="OD")

    def _immo(self, **kwargs):
        defaults = dict(
            designation="Serveur", categorie=self.categorie,
            date_acquisition=date(2026, 1, 1), date_mise_service=date(2026, 1, 1),
            cout_acquisition=Decimal("12000.00"), duree=5, mode_amortissement="LINEAIRE",
            compte_immo=self.c2441, compte_amortissement=self.c2844, compte_dotation=self.c6813,
        )
        defaults.update(kwargs)
        return Immobilisation.objects.create(code=next_code_immobilisation(), **defaults)


class TestCodeImmobilisation(ImmoTestBase):
    def test_code_sequentiel(self):
        assert next_code_immobilisation() == "IMM000001"
        self._immo()
        assert next_code_immobilisation() == "IMM000002"


class TestGenerationPlan(ImmoTestBase):
    def test_genere_dotations_et_passe_en_service(self):
        immo = self._immo()
        lignes = generer_plan_amortissement(immo)
        immo.refresh_from_db()
        assert immo.statut == "EN_SERVICE"
        assert Dotation.objects.filter(immobilisation=immo).count() == len(lignes) == 60
        total = sum(d.montant for d in Dotation.objects.filter(immobilisation=immo))
        assert total == Decimal("12000.00")

    def test_idempotent_ne_duplique_pas(self):
        immo = self._immo()
        generer_plan_amortissement(immo)
        generer_plan_amortissement(immo)
        assert Dotation.objects.filter(immobilisation=immo).count() == 60


class TestComptabilisationDotations(ImmoTestBase):
    def test_genere_piece_od_equilibree_et_marque_comptabilisee(self):
        immo = self._immo()
        generer_plan_amortissement(immo)
        piece = comptabiliser_dotations(self.exercice, 1, self.user)
        assert piece is not None
        assert piece.statut == "VALIDEE"
        assert piece.total_debit == piece.total_credit == Decimal("200.00")
        lignes = LigneEcriture.objects.filter(piece=piece)
        assert lignes.filter(compte=self.c6813, debit=Decimal("200.00")).exists()
        assert lignes.filter(compte=self.c2844, credit=Decimal("200.00")).exists()
        d = Dotation.objects.get(immobilisation=immo, annee=2026, mois=1)
        assert d.statut == "COMPTABILISEE" and d.piece_generee_id == piece.id

    def test_rien_a_comptabiliser_retourne_none(self):
        immo = self._immo()
        generer_plan_amortissement(immo)
        comptabiliser_dotations(self.exercice, 1, self.user)
        assert comptabiliser_dotations(self.exercice, 1, self.user) is None  # idempotent
