"""Pagination partagée (templates/ui/pagination.html).

Deux défauts réels motivent ces tests, au-delà de l'apparence :
  • `tiers_list` paginait à 50 sans afficher le moindre contrôle : les tiers au-delà
    du 50e étaient inatteignables depuis l'interface ;
  • la pagination des pièces écrivait `?page=2` en dur, ce qui effaçait les filtres
    courants — la page 2 d'une liste filtrée montrait des données non filtrées.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.template import RequestContext, Template
from django.test import RequestFactory
from django.urls import reverse

from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()


def _page(numero: int, total: int, par_page: int = 10):
    return Paginator(list(range(total)), par_page).page(numero)


def rendre(page_obj, chemin="/tiers/") -> str:
    # RequestContext, et non Context : `{% querystring %}` lit `context.request`, que
    # seul un RequestContext expose (via le processeur `context_processors.request`,
    # activé dans les réglages — sans lui la pagination lèverait une exception).
    requete = RequestFactory().get(chemin)
    return Template('{% include "ui/pagination.html" %}').render(
        RequestContext(requete, {"page_obj": page_obj})
    )


class TestPagesAffichees:
    def test_rien_ne_s_affiche_sur_une_page_unique(self):
        """Un bandeau de pagination sur une liste de trois lignes est du bruit."""
        assert rendre(_page(1, total=5)).strip() == ""

    def test_la_page_courante_est_marquee(self):
        html = rendre(_page(3, total=100))
        assert 'aria-current="page"' in html
        assert "btn-active" in html

    def test_les_numeros_permettent_d_atteindre_une_page_directement(self):
        html = rendre(_page(1, total=100))
        assert ">2<" in html and ">3<" in html

    def test_ellipses_au_dela_de_quelques_pages(self):
        """Sans élision, 200 pages produiraient 200 boutons."""
        html = rendre(_page(50, total=2000))
        assert "…" in html

    def test_les_fleches_sont_desactivees_aux_extremites(self):
        premiere = rendre(_page(1, total=100))
        # La flèche « précédent » est présente mais inerte, pour ne pas décaler la barre.
        assert premiere.count("btn-disabled") >= 1
        derniere = rendre(_page(10, total=100))
        assert derniere.count("btn-disabled") >= 1

    def test_le_nombre_total_de_lignes_est_indique(self):
        assert "100 lignes" in rendre(_page(1, total=100))


class TestConservationDesFiltres:
    def test_les_parametres_courants_survivent_au_changement_de_page(self):
        """Le défaut d'origine : `?page=2` en dur effaçait le filtre en cours."""
        html = rendre(_page(1, total=100), chemin="/tiers/?type=CLIENT&q=sobe")
        assert "type=CLIENT" in html
        assert "q=sobe" in html

    def test_le_parametre_page_est_remplace_et_non_ajoute(self):
        html = rendre(_page(2, total=100), chemin="/tiers/?page=2&type=CLIENT")
        assert "page=2&amp;page=" not in html and "page=2&page=" not in html


@pytest.fixture
def client_admin(client, db):
    charger_plan_depuis_fichier("syscohada_2017.json")
    societe = provisionner_societe(
        code="PAGE", schema_name="page_soc", raison_sociale="Page SARL", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )
    u = User.objects.create_user(username="page@x.fr", email="page@x.fr", password="x")
    SocieteMembership.objects.create(user=u, societe=societe, role="admin", actif=True)
    client.force_login(u)
    return client, societe


@pytest.mark.django_db
def test_toutes_les_lignes_sont_atteignables_et_aucune_n_est_dupliquee(client_admin):
    """L'invariant qui compte : parcourir toutes les pages doit restituer l'ensemble
    des enregistrements, chacun exactement une fois.

    La vue paginait déjà, mais aucun contrôle n'était affiché : les tiers au-delà de
    la première page étaient inatteignables. On vérifie ici le parcours complet plutôt
    qu'une page précise, pour que le test reste vrai si `paginate_by` change.
    """
    import math

    from django_tenants.utils import tenant_context

    from apps.comptabilite.models import CompteComptable
    from apps.tiers.models import Tiers
    from apps.tiers.views import TiersListView

    client, societe = client_admin
    total = 60
    with tenant_context(societe):
        collectif = CompteComptable.objects.get(numero="4111")
        Tiers.objects.bulk_create([
            Tiers(type_tiers="CLIENT", code_auxiliaire=f"C{i:04d}",
                  compte_collectif=collectif, raison_sociale=f"Client {i}")
            for i in range(total)
        ])

    html = client.get(reverse("tiers:tiers_list")).content.decode()
    assert 'aria-label="Pagination"' in html, "aucun contrôle de pagination affiché"
    assert f"{total} lignes" in html

    nb_pages = math.ceil(total / TiersListView.paginate_by)
    vus: list[str] = []
    for numero in range(1, nb_pages + 1):
        page = client.get(reverse("tiers:tiers_list"), {"page": numero}).content.decode()
        vus += [f"C{i:04d}" for i in range(total) if f"C{i:04d}" in page]

    assert len(vus) == len(set(vus)), "un tiers apparaît sur plusieurs pages"
    assert set(vus) == {f"C{i:04d}" for i in range(total)}, "des tiers ne sont sur aucune page"


@pytest.mark.django_db
def test_la_liste_des_pieces_pagine_au_dela_du_seuil(client_admin):
    """Documente le seuil : tant qu'il n'y a qu'une page, le composant ne s'affiche
    pas — c'est voulu, mais cela se confond facilement avec une pagination cassée.

    Le seuil est lu sur la vue plutôt qu'écrit en dur : le test doit rester vrai si
    `paginate_by` change."""
    from django.core.management import call_command
    from django_tenants.utils import tenant_context

    from apps.comptabilite.models import PieceComptable
    from apps.comptabilite.views import PieceListView

    client, societe = client_admin
    call_command("jeu_demo", "--societe", "PAGE", "--mois", "12")

    with tenant_context(societe):
        total = PieceComptable.objects.count()
    assert total > PieceListView.paginate_by, (
        f"le jeu de démonstration ({total} pièces) ne dépasse pas "
        f"{PieceListView.paginate_by} : ce test ne prouverait rien"
    )

    html = client.get(reverse("comptabilite:piece_list")).content.decode()
    assert 'aria-label="Pagination"' in html
    assert f"{total} lignes" in html


@pytest.mark.django_db
def test_le_filtre_survit_au_changement_de_page_sur_les_pieces(client_admin):
    """Le défaut d'origine : `?page=2` effaçait `?statut=…`."""
    from django.core.management import call_command

    client, _ = client_admin
    call_command("jeu_demo", "--societe", "PAGE", "--mois", "12")

    html = client.get(reverse("comptabilite:piece_list"), {"statut": "VALIDEE"}).content.decode()
    assert "statut=VALIDEE" in html, "le filtre disparaît des liens de pagination"
