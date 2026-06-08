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
from apps.comptabilite.services import cloturer_exercice, valider_piece


class ClotureTestBase(TenantTestCase):
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
        self.c521 = CompteComptable.objects.create(numero="521000", libelle="Banque", classe=5)
        self.c101 = CompteComptable.objects.create(numero="101000", libelle="Capital", classe=1)
        self.c701 = CompteComptable.objects.create(numero="701000", libelle="Ventes", classe=7)
        self.ex = Exercice.objects.create(
            code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31)
        )
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.ex, mois=m)
        self.jvte = Journal.objects.create(code="VTE", libelle="Ventes", type_journal="VENTES")
        self.jan = Journal.objects.create(code="AN", libelle="À-nouveaux", type_journal="AN")

    def _vente_validee(self, montant, date_piece=date(2026, 6, 1)):
        """Encaissement : débit 521 / crédit 701, validé."""
        piece = PieceComptable.objects.create(
            journal=self.jvte, exercice=self.ex, date_piece=date_piece,
            libelle="Vente", statut="BROUILLARD", auteur=self.user,
        )
        LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=self.c521,
                                     debit=montant, credit=Decimal("0.00"))
        LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=self.c701,
                                     debit=Decimal("0.00"), credit=montant)
        return valider_piece(piece, self.user)


class TestCloture(ClotureTestBase):
    def test_cloture_genere_anouveaux_equilibres_et_verrouille(self):
        self._vente_validee(Decimal("1000.00"))
        piece_an = cloturer_exercice(self.ex, self.user)

        assert piece_an.statut == "VALIDEE"
        assert piece_an.total_debit == piece_an.total_credit == Decimal("1000.00")
        ex2027 = Exercice.objects.get(code="2027")
        assert piece_an.exercice_id == ex2027.id
        assert ex2027.exercice_precedent_id == self.ex.id
        assert Periode.objects.filter(exercice=ex2027).count() == 12

        assert LigneEcriture.objects.filter(piece=piece_an, compte=self.c521, debit=Decimal("1000.00")).exists()
        report = CompteComptable.objects.get(numero="12")
        assert LigneEcriture.objects.filter(piece=piece_an, compte=report, credit=Decimal("1000.00")).exists()
        assert not LigneEcriture.objects.filter(piece=piece_an, compte=self.c701).exists()

        self.ex.refresh_from_db()
        assert self.ex.statut == "CLOTURE"
        assert self.ex.cloture_par_id == self.user.id and self.ex.date_cloture is not None
        assert Periode.objects.filter(exercice=self.ex, statut="CLOTUREE").count() == 12
