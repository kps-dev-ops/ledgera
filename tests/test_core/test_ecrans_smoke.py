"""Test de fumee : les ecrans principaux repondent 200 et sont correctement habilles.

Une suite verte n'a jamais empeche une page d'etre cassee a l'affichage : les gabarits
ne sont evalues qu'a la requete, et une classe purgee du CSS ne produit aucune erreur.
Ces cas font donc de vraies requetes HTTP sur une societe reellement provisionnee.
"""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()
RACINE = Path(__file__).resolve().parents[2]

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


class TestSyntaxeDeGabaritNonFuitee:
    """Un `{# ... #}` sur PLUSIEURS lignes n'est pas un commentaire Django.

    Le tokeniseur utilise `{#.*?#}` SANS re.DOTALL : dès que le commentaire passe à
    la ligne, il n'est plus reconnu et son texte sort tel quel dans la page — sans la
    moindre erreur, ni au chargement du gabarit ni au rendu. Six commentaires écrits
    ainsi s'affichaient en clair dans la barre de navigation, dont un assez long pour
    disloquer la mise en page de l'en-tête.
    """

    def test_aucun_gabarit_ne_contient_de_commentaire_multiligne(self):
        import re

        fautifs = []
        for f in (RACINE / "templates").rglob("*.html"):
            texte = f.read_text(encoding="utf-8")
            for m in re.finditer(r"\{#", texte):
                reste = texte[m.start():]
                fin_ligne, fin_commentaire = reste.find("\n"), reste.find("#}")
                if fin_commentaire == -1 or (fin_ligne != -1 and fin_commentaire > fin_ligne):
                    ligne = texte[: m.start()].count("\n") + 1
                    fautifs.append(f"{f.relative_to(RACINE)}:{ligne}")
        assert fautifs == [], (
            "Commentaires `{# #}` s'étendant sur plusieurs lignes — leur texte sera "
            f"affiché dans la page. Utiliser {{% comment %}} : {fautifs}"
        )

    @pytest.mark.django_db
    @pytest.mark.parametrize("nom", ECRANS)
    def test_aucune_syntaxe_de_gabarit_dans_la_page_servie(self, client_admin, nom):
        """La contre-épreuve : on regarde le HTML réellement envoyé au navigateur."""
        html = client_admin.get(reverse(nom)).content.decode()
        for marqueur in ("{#", "#}", "{%", "{{"):
            assert marqueur not in html, f"{nom} : « {marqueur} » présent dans la page servie"
