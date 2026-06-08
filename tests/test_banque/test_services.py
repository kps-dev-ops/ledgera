from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.banque.models import CompteBancaire, LigneReleve, ReleveBancaire
from apps.banque.services import creer_releve_depuis_lignes
from apps.comptabilite.models import (
    CompteComptable,
    Exercice,
    Journal,
    LigneEcriture,
    Periode,
    PieceComptable,
)
from apps.comptabilite.services import valider_piece


class BanqueTestBase(TenantTestCase):
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
        self.c512 = CompteComptable.objects.create(numero="521000", libelle="Banque", classe=5)
        self.c401 = CompteComptable.objects.create(
            numero="401000", libelle="Fournisseurs", classe=4, collectif_tiers=True
        )
        self.c701 = CompteComptable.objects.create(numero="701000", libelle="Ventes", classe=7)
        self.exercice = Exercice.objects.create(
            code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31)
        )
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.exercice, mois=m)
        self.jbq = Journal.objects.create(code="BQ1", libelle="Banque", type_journal="BANQUE")
        self.compte_bancaire = CompteBancaire.objects.create(
            libelle="BOA courant", compte_comptable=self.c512, journal=self.jbq,
            banque_nom="BOA", devise="XOF",
        )

    def _ecriture_banque(self, montant, sens, date_piece, libelle="", contrepartie=None):
        """Crée une pièce banque validée et renvoie la LigneEcriture sur le compte 521.
        sens='D' => encaissement (débit banque) ; sens='C' => décaissement (crédit banque).
        """
        contrepartie = contrepartie or self.c701
        piece = PieceComptable.objects.create(
            journal=self.jbq, exercice=self.exercice, date_piece=date_piece,
            libelle=libelle or "Mouvement banque", statut="BROUILLARD", auteur=self.user,
        )
        if sens == "D":
            LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=self.c512,
                                         libelle=libelle, debit=montant, credit=Decimal("0.00"),
                                         date_operation=date_piece)
            LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=contrepartie,
                                         libelle=libelle, debit=Decimal("0.00"), credit=montant)
        else:
            LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=self.c512,
                                         libelle=libelle, debit=Decimal("0.00"), credit=montant,
                                         date_operation=date_piece)
            LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=contrepartie,
                                         libelle=libelle, debit=montant, credit=Decimal("0.00"))
        valider_piece(piece, self.user)
        return LigneEcriture.objects.get(piece=piece, compte=self.c512)

    def _releve(self, lignes, **kwargs):
        defaults = dict(date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 31),
                        solde_initial=Decimal("0.00"), solde_final=Decimal("0.00"))
        defaults.update(kwargs)
        return creer_releve_depuis_lignes(self.compte_bancaire, lignes, **defaults)


class TestImportReleve(BanqueTestBase):
    def test_creer_releve_depuis_lignes(self):
        releve = self._releve([
            {"date_operation": date(2026, 1, 10), "libelle": "VIR CLIENT", "montant": Decimal("500.00"), "reference_banque": "R1"},
            {"date_operation": date(2026, 1, 12), "libelle": "ACHAT", "montant": Decimal("-200.00"), "reference_banque": "R2"},
        ])
        assert isinstance(releve, ReleveBancaire)
        assert releve.lignes.count() == 2
        assert releve.lignes.filter(statut="NON_POINTEE").count() == 2
        assert releve.lignes.get(reference_banque="R1").montant == Decimal("500.00")
