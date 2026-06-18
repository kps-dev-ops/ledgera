from django import forms

from .models import ConfigurationIS, ConfigurationTVA, RetraitementFiscal


class DeclarationPeriodeForm(forms.Form):
    configuration = forms.ModelChoiceField(queryset=ConfigurationTVA.objects.filter(actif=True))
    annee = forms.IntegerField(min_value=2000, max_value=2100, initial=2026)
    periode_num = forms.IntegerField(min_value=1, max_value=12, initial=1)


class DeclarationISForm(forms.Form):
    configuration = forms.ModelChoiceField(queryset=ConfigurationIS.objects.filter(actif=True))
    exercice = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        from apps.comptabilite.models import Exercice
        super().__init__(*args, **kwargs)
        self.fields["exercice"].queryset = Exercice.objects.all()


class RetraitementForm(forms.ModelForm):
    class Meta:
        model = RetraitementFiscal
        fields = ["libelle", "montant", "sens"]
