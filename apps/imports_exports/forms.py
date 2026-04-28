from django import forms

from apps.comptabilite.models import Exercice, Journal

from .models import ImportJob


class ImportPiecesForm(forms.ModelForm):
    journal = forms.ModelChoiceField(queryset=Journal.objects.filter(actif=True), to_field_name="code")
    exercice = forms.ModelChoiceField(queryset=Exercice.objects.filter(statut="OUVERT"), to_field_name="code")

    class Meta:
        model = ImportJob
        fields = ["fichier", "modele"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.journal_code = self.cleaned_data["journal"].code
        instance.exercice_code = self.cleaned_data["exercice"].code
        if commit:
            instance.save()
        return instance
