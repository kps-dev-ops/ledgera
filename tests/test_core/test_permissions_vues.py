import pytest
from django.contrib.auth import get_user_model

from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()


@pytest.fixture
def societe(db):
    charger_plan_depuis_fichier("syscohada_2017.json")
    return provisionner_societe(
        code="PERM", schema_name="perm_soc", raison_sociale="Perm SARL", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )


def _client_avec_role(client, societe, role):
    u = User.objects.create_user(username=f"{role}@x.fr", email=f"{role}@x.fr", password="x")
    SocieteMembership.objects.create(user=u, societe=societe, role=role, actif=True)
    client.force_login(u)
    return client


@pytest.mark.django_db
def test_middleware_expose_role_et_permissions(client, societe):
    """Couvre le câblage rôle/permissions du middleware (sinon jamais exercé)."""
    c = _client_avec_role(client, societe, "comptable_junior")
    resp = c.get("/etats/balance/")
    assert resp.wsgi_request.role_societe == "comptable_junior"
    assert resp.wsgi_request.permissions == frozenset({"saisir_brouillard", "consulter_etats"})


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["auditeur", "daf_lecture"])
def test_lecture_seule_ne_peut_pas_saisir(client, societe, role):
    c = _client_avec_role(client, societe, role)
    assert c.get("/compta/pieces/nouvelle/").status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["admin", "comptable_senior", "comptable_junior"])
def test_saisie_autorisee(client, societe, role):
    c = _client_avec_role(client, societe, role)
    assert c.get("/compta/pieces/nouvelle/").status_code == 200


@pytest.mark.django_db
def test_junior_ne_peut_pas_valider(client, societe):
    c = _client_avec_role(client, societe, "comptable_junior")
    assert c.post("/compta/pieces/1/valider/").status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["comptable_junior", "comptable_senior", "daf_lecture", "auditeur"])
def test_seul_admin_peut_cloturer(client, societe, role):
    c = _client_avec_role(client, societe, role)
    assert c.get("/compta/cloture/").status_code == 403


@pytest.mark.django_db
def test_admin_peut_acceder_cloture(client, societe):
    c = _client_avec_role(client, societe, "admin")
    assert c.get("/compta/cloture/").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["admin", "comptable_senior", "comptable_junior", "daf_lecture", "auditeur"])
def test_tous_les_roles_consultent_les_etats(client, societe, role):
    c = _client_avec_role(client, societe, role)
    assert c.get("/etats/balance/").status_code == 200


@pytest.mark.django_db
def test_auditeur_ne_peut_pas_creer_immo(client, societe):
    c = _client_avec_role(client, societe, "auditeur")
    assert c.get("/compta/immos/nouvelle/").status_code == 403


@pytest.mark.django_db
def test_junior_ne_peut_pas_comptabiliser_dotations(client, societe):
    c = _client_avec_role(client, societe, "comptable_junior")
    assert c.get("/compta/immos/comptabiliser/").status_code == 403


@pytest.mark.django_db
def test_auditeur_ne_peut_pas_creer_tiers(client, societe):
    c = _client_avec_role(client, societe, "auditeur")
    assert c.get("/tiers/nouveau/").status_code == 403


@pytest.mark.django_db
def test_junior_peut_creer_tiers(client, societe):
    c = _client_avec_role(client, societe, "comptable_junior")
    assert c.get("/tiers/nouveau/").status_code == 200


@pytest.mark.django_db
def test_auditeur_ne_peut_pas_importer_releve(client, societe):
    c = _client_avec_role(client, societe, "auditeur")
    assert c.get("/compta/banque/releves/importer/").status_code == 403


@pytest.mark.django_db
def test_daf_consulte_tva_mais_ne_declare_pas(client, societe):
    c = _client_avec_role(client, societe, "daf_lecture")
    assert c.get("/compta/fiscal/tva/").status_code == 200      # lecture libre
    assert c.post("/compta/fiscal/tva/").status_code == 403     # écriture refusée


@pytest.mark.django_db
def test_senior_peut_poster_declaration_tva(client, societe):
    c = _client_avec_role(client, societe, "comptable_senior")
    # formulaire vide => la vue re-rend (200), l'essentiel est que ce ne soit PAS 403
    assert c.post("/compta/fiscal/tva/").status_code == 200


@pytest.mark.django_db
def test_junior_ne_peut_pas_liquider_tva(client, societe):
    c = _client_avec_role(client, societe, "comptable_junior")
    assert c.get("/compta/fiscal/tva/1/liquider/").status_code == 403
