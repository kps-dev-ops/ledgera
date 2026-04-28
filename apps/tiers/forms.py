from django import forms

from .models import Tiers


class TiersForm(forms.ModelForm):
    class Meta:
        model = Tiers
        fields = [
            "type_tiers", "compte_collectif", "raison_sociale", "forme_juridique",
            "identifiant_fiscal", "adresse", "cp", "ville", "pays",
            "iban", "bic", "delai_reglement_jours", "mode_reglement", "actif",
        ]
        widgets = {
            "raison_sociale": forms.TextInput(attrs={"placeholder": "Raison sociale"}),
        }
