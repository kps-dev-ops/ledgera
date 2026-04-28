from django import forms
from django.forms import inlineformset_factory

from .models import LigneEcriture, PieceComptable


class PieceForm(forms.ModelForm):
    class Meta:
        model = PieceComptable
        fields = ["journal", "exercice", "date_piece", "reference", "libelle"]
        widgets = {
            "date_piece": forms.DateInput(attrs={"type": "date"}),
            "libelle": forms.TextInput(attrs={"placeholder": "Libellé court de la pièce"}),
        }


class LigneEcritureForm(forms.ModelForm):
    class Meta:
        model = LigneEcriture
        fields = ["compte", "tiers", "libelle", "debit", "credit", "date_echeance"]
        widgets = {
            "date_echeance": forms.DateInput(attrs={"type": "date"}),
            "debit": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "credit": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


LigneFormSet = inlineformset_factory(
    PieceComptable,
    LigneEcriture,
    form=LigneEcritureForm,
    extra=2,
    can_delete=True,
    min_num=2,
    validate_min=True,
)
