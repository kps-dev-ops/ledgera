import pytest
from django_tenants.test.client import TenantClient

from apps.tenants.models import Domain, Societe


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Fixture session-scoped : crée le tenant de test une seule fois."""
    pass


@pytest.fixture
def tenant(db):
    """Tenant de test réutilisable dans les tests qui n'utilisent pas TenantTestCase."""
    societe = Societe.objects.create(
        schema_name="test_tenant",
        code="TEST",
        raison_sociale="Société de Test",
        pays="BJ",
        devise="XOF",
        referentiel="SYSCOHADA",
    )
    Domain.objects.create(domain="test.localhost", tenant=societe, is_primary=True)
    return societe


@pytest.fixture
def tenant_client(tenant):
    return TenantClient(tenant)
