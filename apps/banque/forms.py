from django import forms

from .models import CompteBancaire


class CompteBancaireForm(forms.ModelForm):
    class Meta:
        model = CompteBancaire
        fields = ["libelle", "compte_comptable", "journal", "banque_nom", "iban", "bic", "devise", "solde_initial"]


class ImportReleveForm(forms.Form):
    compte_bancaire = forms.ModelChoiceField(queryset=CompteBancaire.objects.all())
    fichier = forms.FileField()
    date_debut = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    date_fin = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    solde_initial = forms.DecimalField(max_digits=15, decimal_places=2, initial=0)
    solde_final = forms.DecimalField(max_digits=15, decimal_places=2, initial=0)
