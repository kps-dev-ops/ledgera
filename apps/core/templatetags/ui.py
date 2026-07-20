"""Composants d'interface qui doivent ENVELOPPER du balisage.

`{% include %}` ne sait pas encadrer un contenu variable : pour un conteneur dont les
enfants changent a chaque page (une barre de filtres), il faut une balise de bloc.
Les composants sans enfants (en-tete de page, badge...) restent de simples gabarits
inclus depuis templates/ui/.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Une seule definition du conteneur de filtres pour toute l'application. Avant, chaque
# ecran ecrivait la sienne : tailles, espacements et presence d'un bouton variaient
# d'une page a l'autre sans raison.
_GABARIT = (
    '<form method="get" class="card bg-base-100 border border-base-300 shadow-sm mb-6">'
    '<div class="card-body py-4 flex-row flex-wrap items-end gap-3">{contenu}</div>'
    "</form>"
)


class _BarreFiltres(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return mark_safe(_GABARIT.format(contenu=self.nodelist.render(context)))  # noqa: S308


@register.simple_tag
def pages_pagination(page_obj, cotes: int = 2, bords: int = 1) -> list[dict]:
    """Liste des pages à afficher, avec ellipses au-delà de quelques dizaines de pages.

    Renvoie des dicts explicites -- {"numero": 3, "actuelle": False} ou {"ellipse": True} --
    plutôt que la valeur sentinelle de Django : la comparer dans un gabarit obligerait
    à écrire le caractère « … » en dur des deux côtés.
    """
    if page_obj is None or page_obj.paginator.num_pages <= 1:
        return []
    pages = page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=cotes, on_ends=bords
    )
    return [
        {"ellipse": True} if p == page_obj.paginator.ELLIPSIS
        else {"numero": p, "actuelle": p == page_obj.number}
        for p in pages
    ]


@register.simple_tag(takes_context=True)
def actif(context, *motifs, classe="active"):
    """Renvoie `classe` si l'écran courant correspond à l'un des motifs, sinon "".

        <a href="…" class="{% actif 'comptabilite:piece_*' %}">Pièces</a>

    Un motif est le nom complet d'une vue (`etats:balance`) ou un préfixe terminé par
    `*` (`etats:*`, `comptabilite:piece_*`).

    Le préfixe est indispensable ici : l'entrée « Pièces » doit rester allumée sur le
    détail et le formulaire d'une pièce, pas seulement sur la liste. Et un simple test
    d'espace de noms ne suffirait pas — `comptabilite` regroupe les pièces, le
    lettrage (rattaché aux tiers) et la clôture (rattachée aux états).
    """
    resolution = getattr(context.get("request"), "resolver_match", None)
    if resolution is None:  # page d'erreur, rendu hors requête
        return ""
    courant = resolution.view_name  # ex. "etats:balance"
    for motif in motifs:
        correspond = courant.startswith(motif[:-1]) if motif.endswith("*") else courant == motif
        if correspond:
            return classe
    return ""


@register.tag("filtres")
def filtres(parser, token):
    """Barre de filtres standard.

        {% filtres %}
            <label class="form-control">
                <span class="label-text mb-1">Exercice</span>
                <select name="exercice" class="select select-sm select-bordered">...</select>
            </label>
            <button class="btn btn-sm btn-primary">Filtrer</button>
        {% endfiltres %}

    Chaque controle porte un libelle : un menu deroulant seul n'apprend pas a
    l'utilisateur ce qu'il filtre.
    """
    nodelist = parser.parse(("endfiltres",))
    parser.delete_first_token()
    return _BarreFiltres(nodelist)
