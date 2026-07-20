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
