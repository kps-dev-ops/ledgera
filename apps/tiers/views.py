from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.decorators import PermissionRequiseMixin

from .forms import TiersForm
from .models import Tiers
from .services import next_code_auxiliaire


class TiersListView(LoginRequiredMixin, ListView):
    model = Tiers
    template_name = "tiers/tiers_list.html"
    context_object_name = "tiers_list"
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset()
        type_tiers = self.request.GET.get("type")
        actif = self.request.GET.get("actif")
        q = self.request.GET.get("q")
        if type_tiers:
            qs = qs.filter(type_tiers=type_tiers)
        if actif in ("0", "1"):
            qs = qs.filter(actif=(actif == "1"))
        if q:
            qs = qs.filter(raison_sociale__icontains=q)
        return qs


class TiersDetailView(LoginRequiredMixin, DetailView):
    model = Tiers
    template_name = "tiers/tiers_detail.html"
    context_object_name = "tiers"


class TiersCreateView(PermissionRequiseMixin, LoginRequiredMixin, CreateView):
    permission_requise = "saisir_brouillard"
    model = Tiers
    form_class = TiersForm
    template_name = "tiers/tiers_form.html"

    def form_valid(self, form):
        form.instance.code_auxiliaire = next_code_auxiliaire(form.cleaned_data["type_tiers"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("tiers:tiers_detail", kwargs={"pk": self.object.pk})


class TiersUpdateView(PermissionRequiseMixin, LoginRequiredMixin, UpdateView):
    permission_requise = "saisir_brouillard"
    model = Tiers
    form_class = TiersForm
    template_name = "tiers/tiers_form.html"

    def get_success_url(self):
        return reverse_lazy("tiers:tiers_detail", kwargs={"pk": self.object.pk})
