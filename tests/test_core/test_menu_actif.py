"""Mise en évidence de l'entrée de menu correspondant à l'écran courant.

Sans repère visuel, l'utilisateur ne sait pas où il se trouve — d'autant que la barre
compte une dizaine d'entrées et deux menus dépliants.
"""

import pytest
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import resolve, reverse

from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()


def rendre_actif(chemin: str, *motifs) -> str:
    """Rend `{% actif %}` comme si la requête portait sur `chemin`."""
    requete = RequestFactory().get(chemin)
    requete.resolver_match = resolve(chemin)
    source = "{% load ui %}{% actif " + " ".join(f"'{m}'" for m in motifs) + " %}"
    return Template(source).render(Context({"request": requete}))


class TestBaliseActif:
    def test_correspondance_exacte(self):
        assert rendre_actif(reverse("etats:balance"), "etats:balance") == "active"
        assert rendre_actif(reverse("etats:balance"), "etats:journal") == ""

    def test_correspondance_par_prefixe(self):
        """L'entrée « Pièces » doit rester allumée sur le détail d'une pièce."""
        assert rendre_actif(reverse("comptabilite:piece_list"), "comptabilite:piece_*") == "active"
        assert rendre_actif("/compta/pieces/1/", "comptabilite:piece_*") == "active"

    def test_un_prefixe_ne_deborde_pas_sur_une_autre_rubrique(self):
        """`comptabilite` mélange pièces, lettrage et clôture : le préfixe doit trancher."""
        cloture = reverse("comptabilite:cloture_liste")
        assert rendre_actif(cloture, "comptabilite:piece_*") == ""
        assert rendre_actif(cloture, "comptabilite:cloture*") == "active"

    def test_plusieurs_motifs(self):
        lettrage = reverse("comptabilite:lettrer")
        assert rendre_actif(lettrage, "tiers:*", "comptabilite:lettrer") == "active"

    def test_sans_requete_resolue_aucune_classe(self):
        """Page d'erreur ou rendu hors requête : ne doit pas lever d'exception."""
        source = "{% load ui %}{% actif 'etats:balance' %}"
        assert Template(source).render(Context({})) == ""


@pytest.fixture
def client_connecte(client, db):
    charger_plan_depuis_fichier("syscohada_2017.json")
    societe = provisionner_societe(
        code="MENU", schema_name="menu_soc", raison_sociale="Menu SARL", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )
    u = User.objects.create_user(username="menu@x.fr", email="menu@x.fr", password="x")
    SocieteMembership.objects.create(user=u, societe=societe, role="admin", actif=True)
    client.force_login(u)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("nom_url", "libelle"),
    [
        ("comptabilite:piece_list", "Pièces"),
        ("tiers:tiers_list", "Tiers"),
        ("immobilisations:immo_list", "Immobilisations"),
        ("banque:compte_list", "Banque"),
        ("fiscal:is_list", "IS"),
        ("etats:balance", "Balance générale"),
        ("imports_exports:import_list", "Imports Excel"),
    ],
)
def test_l_entree_du_menu_est_marquee_sur_son_ecran(client_connecte, nom_url, libelle):
    """Vérification de bout en bout : la classe doit arriver dans le HTML servi."""
    import re

    html = client_connecte.get(reverse(nom_url)).content.decode()
    # On ne cherche que dans la barre : le libellé apparaît aussi dans <title> et
    # dans l'en-tête de la page elle-même.
    barre = html[html.index('class="menu menu-horizontal') : html.index("</header>")]
    # L'élément porteur est un <a> ou un <summary>, éventuellement précédé d'une icône.
    element = re.search(
        r'<(?:a|summary)[^>]*class="([^"]*)"[^>]*>(?:\s*<i[^>]*></i>)?\s*' + re.escape(libelle) + r'\s*<',
        barre,
    )
    assert element, f"entrée « {libelle} » introuvable dans la barre de navigation"
    assert "active" in element.group(1), (
        f"« {libelle} » n'est pas marqué actif sur son propre écran (classes : {element.group(1)!r})"
    )


@pytest.mark.django_db
def test_une_seule_rubrique_de_premier_niveau_est_active(client_connecte):
    """Deux entrées allumées en même temps désorientent autant qu'aucune."""
    html = client_connecte.get(reverse("banque:compte_list")).content.decode()
    barre = html[html.index('class="menu menu-horizontal'): html.index("</header>")]
    assert barre.count("active") == 1, "plus d'une entrée de menu marquée active"


def test_le_style_du_menu_depliant_actif_existe():
    """Garde contre une défaillance muette.

    daisyUI n'habille PAS `summary.active` : sa règle de menu exclut explicitement les
    `details` (`.menu li > :not(ul, .menu-title, details, .btn).active`). Sans la règle
    maison ajoutée dans theme/static_src/src/styles.css, poser la classe sur un
    <summary> n'a aucun effet visible — les entrées « États » et « Imports / Exports »
    resteraient éteintes sur leurs propres écrans, sans la moindre erreur.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "theme/static_src/src/styles.css").read_text(
        encoding="utf-8"
    )
    assert "summary.active" in source, (
        "la règle qui met en évidence un menu dépliant actif a disparu — "
        "le marquage redeviendrait invisible"
    )
