import pytest
from django.db import connection
from django_tenants.test.client import TenantClient
from django_tenants.utils import get_public_schema_name

from apps.tenants.models import Domain, Societe


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Fixture session-scoped : crée le tenant de test une seule fois."""
    pass


@pytest.fixture(autouse=True)
def _restaurer_schema_connexion():
    """Restaure, après chaque test, le schema PG qui était actif avant lui.

    TenantSessionMiddleware lie la connexion au schema du tenant et l'y laisse — comme le
    faisait TenantMainMiddleware. En production c'est sans effet : chaque requête débute par
    set_schema_to_public(). Mais un test exécute du code ORM hors cycle requête : sans
    restauration, le schema fuit d'un test à l'autre et casse les écritures exigeant
    `public` (ex. Societe.objects.create).

    On restaure le schema d'origine plutôt que de forcer `public` : TenantTestCase fixe le
    schema une seule fois dans setUpClass (portée classe), donc forcer `public` en teardown
    ferait tourner les tests suivants de la même classe sur le mauvais schema.
    """
    tenant = getattr(connection, "tenant", None)
    yield
    if tenant is None or tenant.schema_name == get_public_schema_name():
        connection.set_schema_to_public()
    else:
        connection.set_tenant(tenant)


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
