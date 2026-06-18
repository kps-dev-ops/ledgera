from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeclarationISForm, DeclarationPeriodeForm, RetraitementForm
from .models import DeclarationIS, DeclarationTVA
from .services import (
    ajouter_retraitement,
    comptabiliser_impot,
    comptabiliser_liquidation,
    creer_declaration_is,
    creer_declaration_tva,
    generer_bordereau_is_pdf,
    generer_bordereau_pdf,
)


@login_required
def declaration_list(request):
    form = DeclarationPeriodeForm(request.POST or None)
    decl = None
    if request.method == "POST" and form.is_valid():
        decl = creer_declaration_tva(
            form.cleaned_data["configuration"], form.cleaned_data["annee"],
            form.cleaned_data["periode_num"], request.user,
        )
    return render(request, "fiscal/declaration_list.html", {
        "form": form, "declaration": decl,
        "declarations": DeclarationTVA.objects.select_related("configuration")[:50],
    })


@login_required
def liquider(request, pk):
    decl = get_object_or_404(DeclarationTVA, pk=pk)
    if decl.statut != "VALIDEE":
        comptabiliser_liquidation(decl, request.user)
    return redirect("fiscal:declaration_list")


@login_required
def bordereau(request, pk):
    decl = get_object_or_404(DeclarationTVA, pk=pk)
    pdf = generer_bordereau_pdf(decl)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="tva_{decl.annee}_{decl.periode_num:02d}.pdf"'
    return resp


@login_required
def is_list(request):
    form = DeclarationISForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        decl = creer_declaration_is(form.cleaned_data["configuration"], form.cleaned_data["exercice"], request.user)
        return redirect("fiscal:is_detail", pk=decl.pk)
    return render(request, "fiscal/declaration_is.html", {
        "form": form, "declarations": DeclarationIS.objects.select_related("configuration", "exercice")[:50],
    })


@login_required
def is_detail(request, pk):
    decl = get_object_or_404(DeclarationIS, pk=pk)
    if request.method == "POST" and decl.statut != "VALIDEE":
        rf = RetraitementForm(request.POST)
        if rf.is_valid():
            ajouter_retraitement(decl, rf.cleaned_data["libelle"], rf.cleaned_data["montant"], rf.cleaned_data["sens"])
        return redirect("fiscal:is_detail", pk=pk)
    return render(request, "fiscal/declaration_is.html", {
        "declaration": decl, "retraitement_form": RetraitementForm(),
    })


@login_required
def is_comptabiliser(request, pk):
    decl = get_object_or_404(DeclarationIS, pk=pk)
    if decl.statut != "VALIDEE":
        comptabiliser_impot(decl, request.user)
    return redirect("fiscal:is_detail", pk=pk)


@login_required
def is_bordereau(request, pk):
    decl = get_object_or_404(DeclarationIS, pk=pk)
    pdf = generer_bordereau_is_pdf(decl)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="is_{decl.exercice.code}.pdf"'
    return resp
