from django import forms

from .models import Immobilisation


class ImmobilisationForm(forms.ModelForm):
    class Meta:
        model = Immobilisation
        fields = [
            "designation", "categorie", "date_acquisition", "date_mise_service",
            "cout_acquisition", "valeur_residuelle", "duree", "mode_amortissement",
            "compte_immo", "compte_amortissement", "compte_dotation",
        ]
        widgets = {
            "date_acquisition": forms.DateInput(attrs={"type": "date"}),
            "date_mise_service": forms.DateInput(attrs={"type": "date"}),
        }


class CessionForm(forms.Form):
    date_cession = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    prix_cession = forms.DecimalField(max_digits=15, decimal_places=2, min_value=0)
