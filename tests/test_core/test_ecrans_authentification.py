"""Ecrans d'authentification : mise en page dediee.

Le formulaire de connexion heritait du conteneur des ecrans metier, prevu pour des
tableaux pleine largeur : sur un ecran de bureau il s'etirait sur toute la largeur,
sans carte ni centrage.
"""

import pytest
from django.urls import reverse


@pytest.fixture
def html_connexion(client, db):
    return client.get(reverse("account_login")).content.decode()


class TestMiseEnPageEntree:
    def test_le_formulaire_est_contraint_en_largeur(self, html_connexion):
        """Le symptome d'origine : aucune contrainte de largeur."""
        assert "max-w-sm" in html_connexion

    def test_la_barre_de_navigation_metier_est_masquee(self, html_connexion):
        """Un visiteur non connecte n'a acces a aucun ecran metier : la barre
        n'afficherait que le logo, deja present dans la mise en page."""
        assert "menu-horizontal" not in html_connexion

    def test_le_conteneur_des_ecrans_metier_n_est_pas_utilise(self, html_connexion):
        assert '<main class="container mx-auto' not in html_connexion

    def test_le_repere_de_journal_equilibre_est_present(self, html_connexion):
        """Le repere de la page : un extrait de journal ou debit = credit (R1)."""
        assert "Journal des ventes" in html_connexion
        assert "Équilibré" in html_connexion
        # Les deux totaux doivent etre egaux : un exemple faux serait embarrassant
        # sur la page d'accueil d'un logiciel comptable.
        assert html_connexion.count("1 180 000") == 3  # ligne client + 2 totaux

    def test_les_champs_portent_l_habillage_daisyui(self, html_connexion):
        assert "input input-bordered" in html_connexion
        assert "btn btn-primary" in html_connexion


class TestToutesLesPagesDEntree:
    @pytest.mark.parametrize(
        "nom",
        ["account_login", "account_signup", "account_reset_password"],
    )
    def test_la_page_repond_et_utilise_la_mise_en_page_dediee(self, client, db, nom):
        reponse = client.get(reverse(nom))
        assert reponse.status_code == 200
        html = reponse.content.decode()
        assert "max-w-sm" in html, f"{nom} : mise en page d'entrée non appliquée"
        assert "{%" not in html and "{#" not in html, f"{nom} : syntaxe de gabarit visible"
