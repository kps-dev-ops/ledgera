"""Composants d'interface partages (templates/ui/ + templatetag `ui`).

Ils existent pour supprimer une incoherence reelle : les ecrans anciens affichaient un
titre nu et une barre de filtres ecrite a la main (tailles et espacements variables,
menus deroulants sans libelle), tandis que les ecrans recents avaient un en-tete a
icone et des cartes. Deux langages visuels dans la meme application.
"""

from django.template import Context, Template
from django.template.loader import render_to_string


def rendre(source: str, **contexte) -> str:
    return Template(source).render(Context(contexte))


class TestEntete:
    def test_affiche_titre_icone_et_sous_titre(self):
        html = render_to_string(
            "ui/entete.html", {"titre": "Grand livre", "icone": "book-open", "sous_titre": "2026"}
        )
        assert "Grand livre" in html
        assert 'data-lucide="book-open"' in html
        assert "2026" in html

    def test_icone_et_sous_titre_sont_facultatifs(self):
        html = render_to_string("ui/entete.html", {"titre": "Tiers"})
        assert "Tiers" in html
        assert "data-lucide" not in html


class TestBarreDeFiltres:
    def test_enveloppe_le_contenu_dans_un_formulaire_get_standard(self):
        html = rendre('{% load ui %}{% filtres %}<select name="x"></select>{% endfiltres %}')
        assert '<form method="get"' in html
        assert "card bg-base-100" in html
        assert '<select name="x"></select>' in html

    def test_le_contenu_est_evalue_dans_le_contexte_appelant(self):
        """La barre doit pouvoir afficher des variables et des boucles, pas du texte fige."""
        html = rendre(
            "{% load ui %}{% filtres %}{% for e in exercices %}<option>{{ e }}</option>{% endfor %}{% endfiltres %}",
            exercices=["2025", "2026"],
        )
        assert "<option>2025</option>" in html
        assert "<option>2026</option>" in html
