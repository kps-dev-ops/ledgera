"""Test de fumee : les ecrans principaux repondent 200 et sont correctement habilles.

Une suite verte n'a jamais empeche une page d'etre cassee a l'affichage : les gabarits
ne sont evalues qu'a la requete, et une classe purgee du CSS ne produit aucune erreur.
Ces cas font donc de vraies requetes HTTP sur une societe reellement provisionnee.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()

# Les ecrans signales comme incoherents, plus ceux qui partagent les memes composants.
# On passe par les noms d'URL : un chemin en dur ferait passer le test pour un echec
# fonctionnel alors qu'une route a simplement ete renommee.
ECRANS = [
    "dashboard",
    "etats:balance",
    "etats:balance_auxiliaire",
    "etats:grand_livre",
    "etats:journal",
    "etats:bilan",
    "etats:compte_resultat",
    "comptabilite:piece_list",
    "tiers:tiers_list",
    "immobilisations:immo_list",
    "banque:compte_list",
    "fiscal:declaration_list",
    "fiscal:is_list",
    "fiscal:aib_list",
    "imports_exports:import_list",
    "imports_exports:export_list",
]


@pytest.fixture
def client_admin(client, db):
    charger_plan_depuis_fichier("syscohada_2017.json")
    societe = provisionner_societe(
        code="SMOKE", schema_name="smoke_soc", raison_sociale="Smoke SARL", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )
    u = User.objects.create_user(username="admin@x.fr", email="admin@x.fr", password="x")
    SocieteMembership.objects.create(user=u, societe=societe, role="admin", actif=True)
    client.force_login(u)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("nom", ECRANS)
def test_l_ecran_repond_et_est_habille(client_admin, nom):
    url = reverse(nom)
    reponse = client_admin.get(url)
    assert reponse.status_code == 200, f"{url} → HTTP {reponse.status_code}"

    html = reponse.content.decode()
    # Marqueur du bug d'origine : le chevron de crispy-tailwind, rendu geant faute de
    # ses classes de taille et de positionnement.
    assert "pointer-events-none absolute" not in html, f"{url} : chevron crispy réapparu"
    # La feuille de style du projet doit etre chargee, sinon la page sort en HTML nu.
    assert "css/dist/styles.css" in html, f"{url} : feuille de style absente"


@pytest.mark.django_db
def test_les_ecrans_fiscaux_proposent_une_configuration(client_admin):
    """Le symptome « il y a une societe mais pas de donnees » : le menu deroulant
    « Configuration » sortait vide, sans aucun moyen de le remplir."""
    for url in (reverse("fiscal:declaration_list"), reverse("fiscal:aib_list")):
        html = client_admin.get(url).content.decode()
        assert 'name="configuration"' in html, f"{url} : pas de champ configuration"
        # Une option reelle, au-dela du « --------- » vide de Django.
        assert html.count("<option") >= 2, f"{url} : aucune configuration proposée"


@pytest.mark.django_db
def test_les_menus_deroulants_portent_la_classe_daisyui(client_admin):
    """Un <select> sans la classe `select` retombe sur l'apparence native du systeme,
    d'ou l'incoherence visuelle constatee entre ecrans."""
    html = client_admin.get(reverse("fiscal:declaration_list")).content.decode()
    assert "select select-bordered" in html
