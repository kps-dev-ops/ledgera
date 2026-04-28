"""Tests du générateur FEC."""
import csv
from datetime import date
from decimal import Decimal
from io import StringIO

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
from apps.imports_exports.services.fec import FEC_COLONNES, build_fec
from apps.tiers.models import Tiers

User = get_user_model()


@pytest.mark.django_db
class TestFEC(TenantTestCase):

    def setUp(self):
        super().setUp()
        with connection.cursor() as c:
            c.execute("SET LOCAL app.user_id = 1")
            c.execute("SET LOCAL app.user_email = 'test@ledgera.app'")
            c.execute("SET LOCAL app.ip = '127.0.0.1'")
        self.user = User.objects.create_user(username="t@t.fr", email="t@t.fr", password="x")
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
        self.tiers = Tiers.objects.create(
            type_tiers="FOURNISSEUR", code_auxiliaire="F000001",
            compte_collectif=self.c401, raison_sociale="ACME",
        )
        piece = PieceComptable.objects.create(
            journal=self.journal, exercice=self.exercice,
            date_piece=date(2026, 4, 15), reference="FAC-001", libelle="Achat test", auteur=self.user,
        )
        LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=self.c607,
                                     libelle="Achat", debit=Decimal("1000.00"))
        LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=self.c401, tiers=self.tiers,
                                     libelle="Total", credit=Decimal("1000.00"))
        valider_piece(piece, self.user)

    def test_fec_18_colonnes(self):
        content = build_fec(self.exercice)
        reader = csv.reader(StringIO(content), delimiter="\t")
        headers = next(reader)
        self.assertEqual(headers, FEC_COLONNES)
        self.assertEqual(len(headers), 18)

    def test_fec_lignes_correctes(self):
        content = build_fec(self.exercice)
        reader = csv.reader(StringIO(content), delimiter="\t")
        next(reader)  # headers
        rows = list(reader)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "ACH")            # JournalCode
        self.assertEqual(rows[0][3], "20260415")       # EcritureDate ISO
        self.assertEqual(rows[0][11], "1000,00")        # Debit format français

    def test_fec_montants_format_francais(self):
        content = build_fec(self.exercice)
        # Vérifier qu'il n'y a aucun "1000.00" (point décimal interdit) dans les montants
        self.assertNotIn("1000.00", content)
        self.assertIn("1000,00", content)
