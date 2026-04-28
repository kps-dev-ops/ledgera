from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase
from django_tenants.utils import schema_context

from apps.tenants.models import Domain, Societe


class TestSocieteCreation(TestCase):
    def _make_societe(self, schema_name, code, **kwargs):
        defaults = {
            "raison_sociale": f"Société {code}",
            "pays": "BJ",
            "devise": "XOF",
            "referentiel": "SYSCOHADA",
        }
        defaults.update(kwargs)
        s = Societe(schema_name=schema_name, code=code, **defaults)
        s.save()
        return s

    def test_creation_tenant_kps_benin(self):
        societe = self._make_societe("kps_bj", "KPS_BJ", raison_sociale="KPS Bénin SARL")
        Domain.objects.create(domain="kps-benin.localhost", tenant=societe, is_primary=True)
        assert Societe.objects.filter(code="KPS_BJ").exists()
        assert societe.schema_name == "kps_bj"

    def test_societe_str(self):
        societe = self._make_societe("test_str", "TEST_STR", raison_sociale="Société Test Str")
        assert str(societe) == "TEST_STR — Société Test Str"

    def test_isolation_schema_cree_dans_postgresql(self):
        """Vérifie que django-tenants crée bien le schema PG quand auto_create_schema=True."""
        self._make_societe("test_isolation", "TEST_ISO", pays="FR", devise="EUR", referentiel="PCG_FR")
        with schema_context("test_isolation"):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    ["test_isolation"],
                )
                result = cursor.fetchone()
        assert result is not None, "Le schema PostgreSQL n'a pas été créé par django-tenants"

    def test_statut_default_active(self):
        societe = self._make_societe("test_statut", "TEST_STAT")
        assert societe.statut == "active"

    def test_code_unique_raises_integrity_error(self):
        self._make_societe("test_dup1", "DUP_CODE")
        with self.assertRaises(IntegrityError):
            self._make_societe("test_dup2", "DUP_CODE")

    def test_schema_name_invalide_raises_validation_error(self):
        societe = Societe(
            schema_name="Invalid Schema Name",  # espaces + majuscule = invalide
            code="BAD_SCHEMA",
            raison_sociale="Bad Schema Test",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
        )
        with self.assertRaises(ValidationError):
            societe.full_clean()

    def test_exercice_debut_mois_valides(self):
        societe = self._make_societe("test_mois", "TEST_MOIS")
        assert societe.exercice_debut_mois == 1

    def test_exercice_debut_mois_invalide(self):
        societe = Societe(
            schema_name="test_mois_invalide",
            code="TEST_MOIS_INV",
            raison_sociale="Test Mois Invalide",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
            exercice_debut_mois=13,
        )
        with self.assertRaises(ValidationError):
            societe.full_clean()


class TestDomain(TestCase):
    def setUp(self):
        self.societe = Societe.objects.create(
            schema_name="test_domain",
            code="TEST_DOM",
            raison_sociale="Test Domain",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
        )

    def test_domain_creation(self):
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=self.societe,
            is_primary=True,
        )
        assert domain.domain == "test.localhost"
        assert domain.tenant == self.societe
        assert domain.is_primary is True

    def test_domain_str(self):
        domain = Domain.objects.create(
            domain="test-str.localhost", tenant=self.societe, is_primary=True
        )
        assert str(domain) == "test-str.localhost"

    def test_societe_avec_multiple_domains(self):
        Domain.objects.create(domain="primary.localhost", tenant=self.societe, is_primary=True)
        Domain.objects.create(domain="secondary.localhost", tenant=self.societe, is_primary=False)
        assert Domain.objects.filter(tenant=self.societe).count() == 2

    def test_domain_unique_raises_integrity_error(self):
        Domain.objects.create(domain="unique.localhost", tenant=self.societe, is_primary=True)
        societe2 = Societe.objects.create(
            schema_name="test_domain2",
            code="TEST_DOM2",
            raison_sociale="Test Domain 2",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
        )
        with self.assertRaises(IntegrityError):
            Domain.objects.create(domain="unique.localhost", tenant=societe2, is_primary=True)
