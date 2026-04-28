"""Tests des selectors d'états."""
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
    PieceComptable,
)
from apps.comptabilite.services import valider_piece
from apps.etats import selectors
from apps.tiers.models import Tiers

User = get_user_model()


class EtatsTestBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        with connection.cursor() as c:
            c.execute("SET LOCAL app.user_id = 1")
            c.execute("SET LOCAL app.user_email = 'test@ledgera.app'")
            c.execute("SET LOCAL app.ip = '127.0.0.1'")
        self.user = User.objects.create_user(
            username="t@t.fr", email="t@t.fr", password="x"
        )
        self.exercice = Exercice.objects.create(
            code="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31)
        )
        for m in range(1, 13):
            Periode.objects.get_or_create(exercice=self.exercice, mois=m)
        self.c607 = CompteComptable.objects.create(numero="607000", libelle="Achats", classe=6)
        self.c401 = CompteComptable.objects.create(
            numero="401000", libelle="Fournisseurs", classe=4, collectif_tiers=True
        )
        self.journal = Journal.objects.create(code="ACH", libelle="Achats", type_journal="ACHATS")
        self.fournisseur = Tiers.objects.create(
            type_tiers="FOURNISSEUR", code_auxiliaire="F000001",
            compte_collectif=self.c401, raison_sociale="ACME",
        )
        # Créer une pièce validée
        piece = PieceComptable.objects.create(
            journal=self.journal, exercice=self.exercice,
            date_piece=date(2026, 4, 15), libelle="Achat test", auteur=self.user,
        )
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=1, compte=self.c607, debit=Decimal("1000.00")
        )
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=2, compte=self.c401, tiers=self.fournisseur,
            credit=Decimal("1000.00"),
        )
        valider_piece(piece, self.user)


@pytest.mark.django_db
class TestSelectors(EtatsTestBase):

    def test_balance_equilibree(self):
        lignes = list(selectors.balance(self.exercice))
        total_d = sum(row["total_debit"] or 0 for row in lignes)
        total_c = sum(row["total_credit"] or 0 for row in lignes)
        self.assertEqual(total_d, total_c)
        self.assertEqual(total_d, Decimal("1000.00"))

    def test_grand_livre_compte_solde_progressif(self):
        result = selectors.grand_livre_compte(self.c607, self.exercice)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["solde"], Decimal("1000.00"))

    def test_balance_auxiliaire(self):
        lignes = list(selectors.balance_auxiliaire(self.c401, self.exercice))
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["tiers__code_auxiliaire"], "F000001")
        self.assertEqual(lignes[0]["solde"], Decimal("-1000.00"))
