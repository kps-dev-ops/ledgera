import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import tenant_context

from apps.comptabilite.models import CompteComptable
from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()


def _societe(code, schema):
    charger_plan_depuis_fichier("syscohada_2017.json")
    return provisionner_societe(
        code=code, schema_name=schema, raison_sociale=f"Societe {code}", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
        domaine=f"{schema}.local",
    )


def _user(email, societes):
    u = User.objects.create_user(username=email, email=email, password="x")
    for s in societes:
        SocieteMembership.objects.create(user=u, societe=s, role="comptable_senior", actif=True)
    return u


@pytest.mark.django_db
def test_societe_par_defaut(client):
    a = _societe("A", "soc_a")
    u = _user("a@x.fr", [a])
    client.force_login(u)
    resp = client.get("/")
    assert resp.wsgi_request.tenant is not None
    assert resp.wsgi_request.tenant.pk == a.pk


@pytest.mark.django_db
def test_bascule_societe_autorisee(client):
    a, b = _societe("A", "soc_a"), _societe("B", "soc_b")
    u = _user("ab@x.fr", [a, b])
    client.force_login(u)
    resp = client.get(f"/societe/{b.pk}/activer/", follow=True)
    assert resp.wsgi_request.tenant.pk == b.pk
    resp2 = client.get("/")
    assert resp2.wsgi_request.tenant.pk == b.pk


@pytest.mark.django_db
def test_societe_non_habilitee_refusee(client):
    a, b = _societe("A", "soc_a"), _societe("B", "soc_b")
    u = _user("a@x.fr", [a])
    client.force_login(u)
    assert client.get(f"/societe/{b.pk}/activer/").status_code == 404
    session = client.session
    session["societe_id"] = b.pk
    session.save()
    resp = client.get("/")
    assert resp.wsgi_request.tenant.pk == a.pk


@pytest.mark.django_db
def test_isolation_donnees_entre_societes(client):
    a, b = _societe("A", "soc_a"), _societe("B", "soc_b")
    with tenant_context(a):
        CompteComptable.objects.create(numero="999999", libelle="Secret de A", classe=6)
    u_b = _user("b@x.fr", [b])
    client.force_login(u_b)
    resp = client.get("/")
    assert resp.wsgi_request.tenant.pk == b.pk
    with tenant_context(b):
        assert CompteComptable.objects.filter(numero="999999").count() == 0
    with tenant_context(a):
        assert CompteComptable.objects.filter(numero="999999").count() == 1


@pytest.mark.django_db
def test_habilitation_inactive_ignoree(client):
    a = _societe("A", "soc_a")
    u = _user("a@x.fr", [a])
    SocieteMembership.objects.filter(user=u, societe=a).update(actif=False)
    client.force_login(u)
    resp = client.get("/", follow=True)
    assert resp.status_code == 200
    assert resp.wsgi_request.tenant is None


@pytest.mark.django_db
def test_non_authentifie_pas_de_tenant(client):
    _societe("A", "soc_a")
    resp = client.get("/")
    assert resp.status_code in (301, 302)
