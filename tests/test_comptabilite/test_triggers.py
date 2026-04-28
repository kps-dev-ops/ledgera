"""Tests d'intégration des triggers PostgreSQL R1-R7.

Ces tests exigent une base PG accessible. Si l'auth PG locale échoue, ils sont
skippés proprement avec un message clair.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.utils import InternalError
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
from apps.tiers.models import Tiers

User = get_user_model()


class TriggersTestBase(TenantTestCase):
    """Setup commun : exercice 2026 + plan minimal (607, 44566, 401, 411) + journal ACH."""

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
        self.user = User.objects.create_user(
            username="test@ledgera.app", email="test@ledgera.app", password="testpass"
        )
        self.exercice = Exercice.objects.create(
            code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31)
        )
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.exercice, mois=m)
        self.c607 = CompteComptable.objects.create(numero="607000", libelle="Achats", classe=6)
        self.c44566 = CompteComptable.objects.create(numero="445660", libelle="TVA déductible", classe=4)
        self.c401 = CompteComptable.objects.create(
            numero="401000", libelle="Fournisseurs", classe=4, collectif_tiers=True
        )
        self.c411 = CompteComptable.objects.create(
            numero="411000", libelle="Clients", classe=4, collectif_tiers=True
        )
        self.journal_ach = Journal.objects.create(code="ACH", libelle="Achats", type_journal="ACHATS")
        self.fournisseur = Tiers.objects.create(
            type_tiers="FOURNISSEUR", code_auxiliaire="F000001",
            compte_collectif=self.c401, raison_sociale="Fournisseur Test",
        )

    def _piece_ach_valide(self):
        """Crée une pièce d'achat équilibrée 11800 = 10000+1800."""
        piece = PieceComptable.objects.create(
            journal=self.journal_ach, exercice=self.exercice,
            date_piece=date(2026, 4, 15), libelle="Test", auteur=self.user,
        )
        LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=self.c607,
                                     libelle="Achat", debit=Decimal("10000.00"))
        LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=self.c44566,
                                     libelle="TVA", debit=Decimal("1800.00"))
        LigneEcriture.objects.create(piece=piece, numero_ligne=3, compte=self.c401,
                                     tiers=self.fournisseur, libelle="Total", credit=Decimal("11800.00"))
        return piece


@pytest.mark.django_db
class TestTriggersR1R7(TriggersTestBase):

    def test_R1_piece_non_equilibree_rejetee(self):
        piece = self._piece_ach_valide()
        # Forcer un déséquilibre puis tenter de la VALIDER directement en SQL
        piece.total_debit = Decimal("10000.00")
        piece.total_credit = Decimal("9000.00")
        piece.statut = "VALIDEE"
        piece.numero = 1
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                piece.save()

    def test_R2_periode_verrouillee_bloque(self):
        Periode.objects.filter(exercice=self.exercice, mois=4).update(statut="VERROUILLEE")
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                PieceComptable.objects.create(
                    journal=self.journal_ach, exercice=self.exercice,
                    date_piece=date(2026, 4, 10), libelle="Bloquée", auteur=self.user,
                )

    def test_R3_update_piece_validee_interdit(self):
        piece = self._piece_ach_valide()
        valider_piece(piece, self.user)
        piece.refresh_from_db()
        piece.libelle = "Modifié après validation"
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                piece.save()

    def test_R3_delete_piece_validee_interdit(self):
        piece = self._piece_ach_valide()
        valider_piece(piece, self.user)
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                piece.delete()

    def test_R4_numero_attribue_sequentiel(self):
        numeros = []
        for _ in range(3):
            p = self._piece_ach_valide()
            valider_piece(p, self.user)
            p.refresh_from_db()
            numeros.append(p.numero)
        self.assertEqual(numeros, [1, 2, 3])

    def test_R5_date_hors_exercice_rejetee(self):
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                PieceComptable.objects.create(
                    journal=self.journal_ach, exercice=self.exercice,
                    date_piece=date(2027, 1, 1), libelle="Hors exo", auteur=self.user,
                )

    def test_R7_compte_collectif_sans_tiers(self):
        piece = PieceComptable.objects.create(
            journal=self.journal_ach, exercice=self.exercice,
            date_piece=date(2026, 4, 15), libelle="Test R7", auteur=self.user,
        )
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                LigneEcriture.objects.create(
                    piece=piece, numero_ligne=1, compte=self.c401,
                    tiers=None, debit=Decimal("100.00"),
                )

    def test_R7_compte_non_collectif_avec_tiers(self):
        piece = PieceComptable.objects.create(
            journal=self.journal_ach, exercice=self.exercice,
            date_piece=date(2026, 4, 15), libelle="Test R7 inverse", auteur=self.user,
        )
        with self.assertRaises((IntegrityError, InternalError)):
            with transaction.atomic():
                LigneEcriture.objects.create(
                    piece=piece, numero_ligne=1, compte=self.c607,
                    tiers=self.fournisseur, debit=Decimal("100.00"),
                )
