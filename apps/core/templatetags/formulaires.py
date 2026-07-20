"""Habillage daisyUI des champs de formulaire.

Pourquoi ce module existe plutot que crispy-tailwind : Tailwind purge toute classe
qu'il ne voit pas dans les sources qu'il scanne, et il ne scanne que `templates/` et
`apps/` (theme/static_src/tailwind.config.js ; l'etape Node du Dockerfile ne copie
d'ailleurs que ces dossiers, sans aucun paquet Python). Les classes ecrites par un
gabarit de site-packages sont donc systematiquement absentes du CSS compile.

Consequence : toute classe utilitaire destinee a un formulaire doit etre ecrite ICI ou
dans templates/ui/, jamais deleguee a une dependance.
"""

from django import forms
from django.template import Library

register = Library()

# (famille de widget, classe daisyUI, classe d'etat d'erreur).
# L'ordre compte : on retient la PREMIERE famille correspondante, et la hierarchie
# Django place les sous-classes avant leurs parents (CheckboxSelectMultiple derive de
# RadioSelect, SelectMultiple de Select, ClearableFileInput de FileInput).
#
# Aucune classe de LARGEUR ici : c'est le gabarit qui la fournit, via l'argument du
# filtre. Un meme formulaire se rend empile (`w-full`) ou en ligne (largeur auto)
# selon l'ecran, et ce choix n'appartient pas au widget.
_FAMILLES: tuple[tuple[type[forms.Widget], str, str], ...] = (
    (forms.CheckboxSelectMultiple, "checkbox checkbox-primary", "checkbox-error"),
    (forms.RadioSelect, "radio radio-primary", "radio-error"),
    (forms.CheckboxInput, "checkbox checkbox-primary", "checkbox-error"),
    (forms.ClearableFileInput, "file-input file-input-bordered", "file-input-error"),
    (forms.FileInput, "file-input file-input-bordered", "file-input-error"),
    (forms.SelectMultiple, "select select-bordered", "select-error"),
    (forms.Select, "select select-bordered", "select-error"),
    (forms.Textarea, "textarea textarea-bordered", "textarea-error"),
)
_DEFAUT = ("input input-bordered", "input-error")

# Les cases a cocher et radios ne prennent jamais de largeur : ce sont des pastilles
# de taille fixe, `w-full` les etirerait sur toute la ligne.
_SANS_LARGEUR = (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)


def _habillage(widget) -> tuple[str, str]:
    for famille, classe, classe_erreur in _FAMILLES:
        if isinstance(widget, famille):
            return classe, classe_erreur
    return _DEFAUT


@register.filter
def widget_daisy(field, largeur=""):
    """Rend le champ avec la classe daisyUI de sa famille, plus la largeur demandee
    par le gabarit et l'etat d'erreur le cas echeant."""
    widget = field.field.widget
    classe, classe_erreur = _habillage(widget)
    attrs = dict(widget.attrs)
    # On complete la classe existante au lieu de l'ecraser : certains formulaires
    # posent deja des attributs de widget (placeholder, step, type="date"...).
    classes = [attrs.get("class", ""), classe]
    if largeur and not isinstance(widget, _SANS_LARGEUR):
        classes.append(largeur)
    if field.errors:
        classes.append(classe_erreur)
    attrs["class"] = " ".join(c for c in classes if c)
    return field.as_widget(attrs=attrs)


@register.filter
def est_case_a_cocher(field) -> bool:
    """Case a cocher unique : le libelle se place a DROITE du controle."""
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def est_liste_de_choix(field) -> bool:
    """Groupe de radios/cases : ne doit pas etre enveloppe dans un <label> unique,
    qui ferait basculer la premiere option a chaque clic sur le libelle du groupe."""
    return isinstance(field.field.widget, (forms.RadioSelect, forms.CheckboxSelectMultiple))
