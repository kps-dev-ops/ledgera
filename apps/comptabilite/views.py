from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from apps.core.decorators import exige_permission

from .forms import LigneFormSet, PieceForm
from .models import Exercice, LigneEcriture, PieceComptable
from .selectors import apercu_cloture, search_comptes, search_tiers
from .services import cloturer_exercice, delettrer, lettrer, valider_piece


class PieceListView(LoginRequiredMixin, ListView):
    model = PieceComptable
    template_name = "comptabilite/piece_list.html"
    context_object_name = "pieces"
    paginate_by = 50

    def get_queryset(self):
        qs = PieceComptable.objects.select_related("journal", "exercice", "auteur")
        statut = self.request.GET.get("statut")
        journal = self.request.GET.get("journal")
        if statut:
            qs = qs.filter(statut=statut)
        if journal:
            qs = qs.filter(journal__code=journal)
        return qs


class PieceDetailView(LoginRequiredMixin, DetailView):
    model = PieceComptable
    template_name = "comptabilite/piece_detail.html"
    context_object_name = "piece"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lignes"] = self.object.lignes.select_related("compte", "tiers").order_by("numero_ligne")
        return ctx


@login_required
@exige_permission("saisir_brouillard")
def piece_create(request):
    if request.method == "POST":
        form = PieceForm(request.POST)
        formset = LigneFormSet(request.POST, prefix="lignes")
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                piece = form.save(commit=False)
                piece.auteur = request.user
                piece.save()
                formset.instance = piece
                lignes = formset.save(commit=False)
                for i, ligne in enumerate(lignes, start=1):
                    ligne.numero_ligne = i
                    ligne.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, f"Pièce {piece} enregistrée en brouillard.")
            return redirect("comptabilite:piece_detail", pk=piece.pk)
    else:
        form = PieceForm()
        formset = LigneFormSet(prefix="lignes")
    return render(request, "comptabilite/piece_form.html", {"form": form, "formset": formset, "mode": "create"})


@login_required
@exige_permission("saisir_brouillard")
def piece_update(request, pk):
    piece = get_object_or_404(PieceComptable, pk=pk)
    if piece.statut != "BROUILLARD":
        return HttpResponseForbidden("Seuls les brouillards sont modifiables (R3).")
    if request.method == "POST":
        form = PieceForm(request.POST, instance=piece)
        formset = LigneFormSet(request.POST, instance=piece, prefix="lignes")
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                piece = form.save()
                lignes = formset.save(commit=False)
                for i, ligne in enumerate(lignes, start=1):
                    ligne.numero_ligne = i
                    ligne.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, "Pièce mise à jour.")
            return redirect("comptabilite:piece_detail", pk=piece.pk)
    else:
        form = PieceForm(instance=piece)
        formset = LigneFormSet(instance=piece, prefix="lignes")
    return render(request, "comptabilite/piece_form.html",
                  {"form": form, "formset": formset, "mode": "update", "piece": piece})


@login_required
@exige_permission("valider_piece")
def piece_valider_view(request, pk):
    piece = get_object_or_404(PieceComptable, pk=pk)
    if request.method != "POST":
        return HttpResponseForbidden("POST requis")
    try:
        valider_piece(piece, request.user)
        messages.success(request, f"Pièce validée — n° {piece.journal.code}/{piece.numero}")
    except Exception as e:
        messages.error(request, f"Validation refusée : {e}")
    return redirect("comptabilite:piece_detail", pk=piece.pk)


# --- HTMX endpoints ---

@login_required
def htmx_comptes_search(request):
    q = request.GET.get("q", "").strip()
    comptes = search_comptes(q, limit=15)
    target = request.GET.get("target", "")
    return render(request, "comptabilite/partials/compte_options.html",
                  {"comptes": comptes, "target": target})


@login_required
def htmx_tiers_search(request):
    q = request.GET.get("q", "").strip()
    type_tiers = request.GET.get("type") or None
    tiers = search_tiers(q, type_tiers=type_tiers, limit=15)
    target = request.GET.get("target", "")
    return render(request, "comptabilite/partials/tiers_options.html",
                  {"tiers": tiers, "target": target})


@login_required
def htmx_nouvelle_ligne(request):
    """Renvoie une nouvelle ligne vide (formset). Index passé en GET."""
    index = int(request.GET.get("index", 0))
    formset = LigneFormSet(prefix="lignes")
    new_form = formset.empty_form
    new_form.prefix = f"lignes-{index}"
    return render(request, "comptabilite/partials/ligne_form.html", {"form_ligne": new_form})


@login_required
def htmx_totaux(request):
    """Recalcule total débit / crédit à partir du POST partiel."""
    total_d = Decimal("0.00")
    total_c = Decimal("0.00")
    for key, value in request.POST.items():
        if not value:
            continue
        try:
            v = Decimal(value)
        except (InvalidOperation, TypeError):
            continue
        if key.endswith("-debit"):
            total_d += v
        elif key.endswith("-credit"):
            total_c += v
    return render(request, "comptabilite/partials/totaux.html",
                  {"total_debit": total_d, "total_credit": total_c, "equilibre": total_d == total_c and total_d > 0})


# --- Lettrage manuel ---

@login_required
def grand_livre_tiers(request, tiers_id):
    from apps.tiers.models import Tiers

    tiers = get_object_or_404(Tiers, pk=tiers_id)
    lignes = (
        LigneEcriture.objects.filter(tiers=tiers, piece__statut="VALIDEE")
        .select_related("piece", "piece__journal", "compte")
        .order_by("lettre_lettrage", "piece__date_piece", "id")
    )
    non_lettrees = [ligne for ligne in lignes if not ligne.lettre_lettrage]
    lettrees = [ligne for ligne in lignes if ligne.lettre_lettrage]
    return render(request, "comptabilite/grand_livre_tiers.html",
                  {"tiers": tiers, "non_lettrees": non_lettrees, "lettrees": lettrees})


@login_required
@exige_permission("saisir_brouillard")
def lettrer_view(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST requis")
    ids = request.POST.getlist("ligne_ids")
    if not ids:
        messages.error(request, "Aucune ligne sélectionnée")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    qs = LigneEcriture.objects.filter(pk__in=ids)
    try:
        code = lettrer(qs)
        messages.success(request, f"Lettrage effectué — code {code}")
    except ValueError as e:
        messages.error(request, f"Lettrage refusé : {e}")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@exige_permission("saisir_brouillard")
def delettrer_view(request, tiers_id, code_lettre):
    if request.method != "POST":
        return HttpResponseForbidden("POST requis")
    n = delettrer(tiers_id, code_lettre)
    messages.success(request, f"Délettré : {n} lignes (code {code_lettre})")
    return redirect("comptabilite:grand_livre_tiers", tiers_id=tiers_id)


@login_required
@exige_permission("saisir_brouillard")
def piece_supprimer_brouillard(request, pk):
    piece = get_object_or_404(PieceComptable, pk=pk)
    if piece.statut != "BROUILLARD":
        return HttpResponseForbidden("Seuls les brouillards sont supprimables (R3).")
    if request.method == "POST":
        piece.delete()
        messages.success(request, "Brouillard supprimé.")
        return redirect("comptabilite:piece_list")
    return HttpResponseForbidden("POST requis")


# --- Clôture d'exercice ---

@login_required
@exige_permission("cloturer_exercice")
def cloture_liste(request):
    return render(request, "comptabilite/cloture.html", {"exercices": Exercice.objects.all()})


@login_required
@exige_permission("cloturer_exercice")
def cloture(request, pk):
    exercice = get_object_or_404(Exercice, pk=pk)
    if request.method == "POST" and exercice.statut != "CLOTURE":
        try:
            piece = cloturer_exercice(exercice, request.user)
            return render(request, "comptabilite/cloture.html", {
                "exercice": exercice, "apercu": apercu_cloture(exercice),
                "piece_an": piece, "fait": True,
            })
        except ValueError as e:
            return render(request, "comptabilite/cloture.html", {
                "exercice": exercice, "apercu": apercu_cloture(exercice), "erreur": str(e),
            })
    return render(request, "comptabilite/cloture.html", {
        "exercice": exercice, "apercu": apercu_cloture(exercice),
    })
