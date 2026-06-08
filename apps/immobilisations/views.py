from datetime import date as _date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.comptabilite.models import Exercice

from .exports import tableau_immobilisations_xlsx
from .forms import CessionForm, ImmobilisationForm
from .models import CategorieImmobilisation, Immobilisation
from .services import (
    ceder_immobilisation,
    comptabiliser_dotations,
    generer_plan_amortissement,
    next_code_immobilisation,
)


class ImmobilisationListView(LoginRequiredMixin, ListView):
    model = Immobilisation
    template_name = "immobilisations/immobilisation_list.html"
    context_object_name = "immobilisations"


class ImmobilisationCreateView(LoginRequiredMixin, CreateView):
    model = Immobilisation
    form_class = ImmobilisationForm
    template_name = "immobilisations/immobilisation_form.html"

    def form_valid(self, form):
        form.instance.code = next_code_immobilisation()
        response = super().form_valid(form)
        generer_plan_amortissement(self.object)
        return response

    def get_success_url(self):
        return reverse_lazy("immobilisations:immo_detail", kwargs={"pk": self.object.pk})


class ImmobilisationUpdateView(LoginRequiredMixin, UpdateView):
    model = Immobilisation
    form_class = ImmobilisationForm
    template_name = "immobilisations/immobilisation_form.html"

    def get_success_url(self):
        return reverse_lazy("immobilisations:immo_detail", kwargs={"pk": self.object.pk})


class ImmobilisationDetailView(LoginRequiredMixin, DetailView):
    model = Immobilisation
    template_name = "immobilisations/immobilisation_detail.html"
    context_object_name = "immo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dotations"] = self.object.dotations.all()
        ctx["cession_form"] = CessionForm()
        return ctx


def comptes_categorie(request):
    """Endpoint HTMX : renvoie les comptes/durée/mode par défaut d'une catégorie."""
    categorie = get_object_or_404(CategorieImmobilisation, pk=request.GET.get("categorie"))
    return render(request, "immobilisations/partials/comptes_categorie.html", {"c": categorie})


def ceder(request, pk):
    immo = get_object_or_404(Immobilisation, pk=pk)
    form = CessionForm(request.POST)
    if form.is_valid():
        ceder_immobilisation(
            immo, form.cleaned_data["date_cession"], form.cleaned_data["prix_cession"], request.user
        )
    return redirect("immobilisations:immo_detail", pk=pk)


def comptabiliser(request):
    exercices = Exercice.objects.all()
    if request.method == "POST":
        exercice = get_object_or_404(Exercice, pk=request.POST.get("exercice"))
        mois = int(request.POST.get("mois"))
        piece = comptabiliser_dotations(exercice, mois, request.user)
        return render(
            request, "immobilisations/comptabiliser_dotations.html",
            {"exercices": exercices, "piece": piece, "fait": True},
        )
    return render(
        request, "immobilisations/comptabiliser_dotations.html", {"exercices": exercices}
    )


def export_tableau_xlsx(request):
    d = request.GET.get("date")
    date_ref = _date.fromisoformat(d) if d else _date.today()
    contenu = tableau_immobilisations_xlsx(date_ref)
    response = HttpResponse(
        contenu, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="immobilisations_{date_ref}.xlsx"'
    return response
