from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from apps.comptabilite.models import LigneEcriture

from .forms import CompteBancaireForm, ImportReleveForm
from .models import CompteBancaire, LigneReleve, ReleveBancaire
from .selectors import etat_rapprochement
from .services import (
    creer_releve_depuis_lignes,
    depointer,
    lire_lignes_csv,
    lire_lignes_excel,
    pointer_automatiquement,
    pointer_manuellement,
)


class CompteBancaireListView(LoginRequiredMixin, ListView):
    model = CompteBancaire
    template_name = "banque/compte_list.html"
    context_object_name = "comptes"


class CompteBancaireCreateView(LoginRequiredMixin, CreateView):
    model = CompteBancaire
    form_class = CompteBancaireForm
    template_name = "banque/compte_form.html"
    success_url = reverse_lazy("banque:compte_list")


def importer_releve(request):
    form = ImportReleveForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        f = form.cleaned_data["fichier"]
        if f.name.lower().endswith(".csv"):
            lignes = lire_lignes_csv(f)
        else:
            lignes = lire_lignes_excel(f)
        releve = creer_releve_depuis_lignes(
            form.cleaned_data["compte_bancaire"], lignes,
            date_debut=form.cleaned_data["date_debut"], date_fin=form.cleaned_data["date_fin"],
            solde_initial=form.cleaned_data["solde_initial"], solde_final=form.cleaned_data["solde_final"],
        )
        return redirect("banque:rapprochement", pk=releve.pk)
    return render(request, "banque/releve_import.html", {"form": form})


def rapprochement(request, pk):
    releve = get_object_or_404(ReleveBancaire, pk=pk)
    ctx = {"releve": releve, "lignes": releve.lignes.all(), "etat": etat_rapprochement(releve)}
    return render(request, "banque/rapprochement.html", ctx)


def pointer_auto(request, pk):
    releve = get_object_or_404(ReleveBancaire, pk=pk)
    pointer_automatiquement(releve)
    return redirect("banque:rapprochement", pk=pk)


def pointer_manuel(request, ligne_pk):
    ligne = get_object_or_404(LigneReleve, pk=ligne_pk)
    ecriture = get_object_or_404(LigneEcriture, pk=request.POST.get("ecriture"))
    try:
        pointer_manuellement(ligne, ecriture)
    except ValueError:
        pass
    return redirect("banque:rapprochement", pk=ligne.releve_id)


def depointer_ligne(request, ligne_pk):
    ligne = get_object_or_404(LigneReleve, pk=ligne_pk)
    depointer(ligne)
    return redirect("banque:rapprochement", pk=ligne.releve_id)
