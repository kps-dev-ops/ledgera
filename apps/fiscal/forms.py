from django import forms

from .models import ConfigurationTVA


class DeclarationPeriodeForm(forms.Form):
    configuration = forms.ModelChoiceField(queryset=ConfigurationTVA.objects.filter(actif=True))
    annee = forms.IntegerField(min_value=2000, max_value=2100, initial=2026)
    periode_num = forms.IntegerField(min_value=1, max_value=12, initial=1)
