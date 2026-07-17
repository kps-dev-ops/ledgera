from datetime import date as _date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.comptabilite.models import Exercice
from apps.core.decorators import PermissionRequiseMixin, exige_permission

from .exports import tableau_immobilisations_xlsx
from .forms import CessionForm, ImmobilisationForm
from .models import CategorieImmobilisation, Immobilisation
from .selectors import tableau_immobilisations
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = _date.today()
        par_code = {ligne["code"]: ligne for ligne in tableau_immobilisations(today)}
        rows = []
        for immo in ctx["immobilisations"]:
            info = par_code.get(immo.code, {})
            cumul = info.get("cumul_amortissements", 0)
            vnc = info.get("vnc", immo.cout_acquisition)
            taux = (cumul / immo.cout_acquisition * 100) if immo.cout_acquisition else 0
            rows.append({"immo": immo, "cumul": cumul, "vnc": vnc, "taux": taux})
        ctx["rows"] = rows
        ctx["total_brut"] = sum((r["immo"].cout_acquisition for r in rows), 0)
        ctx["total_cumul"] = sum((r["cumul"] for r in rows), 0)
        ctx["total_vnc"] = sum((r["vnc"] for r in rows), 0)
        ctx["nb_en_service"] = sum(1 for r in rows if r["immo"].statut == "EN_SERVICE")
        ctx["nb_sorties"] = sum(1 for r in rows if r["immo"].statut in ("CEDEE", "REBUT"))
        return ctx


class ImmobilisationCreateView(PermissionRequiseMixin, LoginRequiredMixin, CreateView):
    permission_requise = "saisir_brouillard"
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


class ImmobilisationUpdateView(PermissionRequiseMixin, LoginRequiredMixin, UpdateView):
    permission_requise = "saisir_brouillard"
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
        immo = self.object
        dotations = list(immo.dotations.all())
        ctx["dotations"] = dotations
        ctx["cession_form"] = CessionForm()
        cumul = sum((d.montant for d in dotations if d.statut == "COMPTABILISEE"), 0)
        ctx["cumul_comptabilise"] = cumul
        ctx["vnc_actuelle"] = immo.cout_acquisition - cumul
        ctx["base_amortissable"] = immo.cout_acquisition - immo.valeur_residuelle
        ctx["taux_amorti"] = (
            (cumul / immo.cout_acquisition * 100) if immo.cout_acquisition else 0
        )
        ctx["nb_comptabilisees"] = sum(1 for d in dotations if d.statut == "COMPTABILISEE")
        ctx["nb_dotations"] = len(dotations)
        return ctx


def comptes_categorie(request):
    """Endpoint HTMX : renvoie les comptes/durée/mode par défaut d'une catégorie."""
    categorie = get_object_or_404(CategorieImmobilisation, pk=request.GET.get("categorie"))
    return render(request, "immobilisations/partials/comptes_categorie.html", {"c": categorie})


@exige_permission("valider_piece")
def ceder(request, pk):
    immo = get_object_or_404(Immobilisation, pk=pk)
    form = CessionForm(request.POST)
    if form.is_valid():
        ceder_immobilisation(
            immo, form.cleaned_data["date_cession"], form.cleaned_data["prix_cession"], request.user
        )
    return redirect("immobilisations:immo_detail", pk=pk)


@exige_permission("valider_piece")
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
