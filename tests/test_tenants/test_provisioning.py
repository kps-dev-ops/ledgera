from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from django.db import connection
from apps.tenants.models import Societe, Domain


class TestSocieteCreation(TestCase):
    def test_creation_tenant_kps_benin(self):
        societe = Societe(
            schema_name="kps_bj",
            code="KPS_BJ",
            raison_sociale="KPS Bénin SARL",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
        )
        societe.save()

        Domain.objects.create(
            domain="kps-benin.localhost",
            tenant=societe,
            is_primary=True,
        )

        assert Societe.objects.filter(code="KPS_BJ").exists()
        assert societe.schema_name == "kps_bj"

    def test_societe_str(self):
        societe = Societe(
            schema_name="test_str",
            code="TEST_STR",
            raison_sociale="Société Test Str",
            pays="FR",
            devise="EUR",
            referentiel="PCG_FR",
        )
        societe.save()
        assert str(societe) == "TEST_STR — Société Test Str"

    def test_isolation_schema_cree_dans_postgresql(self):
        """Vérifie que django-tenants crée bien le schema PG quand auto_create_schema=True."""
        societe = Societe(
            schema_name="test_isolation",
            code="TEST_ISO",
            raison_sociale="Test Isolation",
            pays="FR",
            devise="EUR",
            referentiel="PCG_FR",
        )
        societe.save()

        with schema_context("test_isolation"):
            cursor = connection.cursor()
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                ["test_isolation"],
            )
            result = cursor.fetchone()
        assert result is not None, "Le schema PostgreSQL n'a pas été créé par django-tenants"

    def test_statut_default_active(self):
        societe = Societe(
            schema_name="test_statut",
            code="TEST_STAT",
            raison_sociale="Test Statut",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
        )
        societe.save()
        assert societe.statut == "active"


class TestDomain(TestCase):
    def setUp(self):
        self.societe = Societe(
            schema_name="test_domain",
            code="TEST_DOM",
            raison_sociale="Test Domain",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
        )
        self.societe.save()

    def test_domain_creation(self):
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=self.societe,
            is_primary=True,
        )
        assert domain.domain == "test.localhost"
        assert domain.tenant == self.societe
        assert domain.is_primary is True

    def test_societe_avec_multiple_domains(self):
        Domain.objects.create(
            domain="primary.localhost", tenant=self.societe, is_primary=True
        )
        Domain.objects.create(
            domain="secondary.localhost", tenant=self.societe, is_primary=False
        )
        assert Domain.objects.filter(tenant=self.societe).count() == 2
