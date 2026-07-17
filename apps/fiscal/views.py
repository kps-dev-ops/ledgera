from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import exige_permission

from .forms import DeclarationAIBForm, DeclarationISForm, DeclarationPeriodeForm, RetraitementForm
from .models import DeclarationAIB, DeclarationIS, DeclarationTVA
from .services import (
    ajouter_retraitement,
    comptabiliser_aib,
    comptabiliser_impot,
    comptabiliser_liquidation,
    creer_declaration_aib,
    creer_declaration_is,
    creer_declaration_tva,
    generer_bordereau_aib_pdf,
    generer_bordereau_is_pdf,
    generer_bordereau_pdf,
)


@login_required
@exige_permission("editer_declarations", methodes=("POST",))
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
@exige_permission("valider_piece")
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
@exige_permission("editer_declarations", methodes=("POST",))
def is_list(request):
    form = DeclarationISForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        decl = creer_declaration_is(form.cleaned_data["configuration"], form.cleaned_data["exercice"], request.user)
        return redirect("fiscal:is_detail", pk=decl.pk)
    return render(request, "fiscal/declaration_is.html", {
        "form": form, "declarations": DeclarationIS.objects.select_related("configuration", "exercice")[:50],
    })


@login_required
@exige_permission("editer_declarations", methodes=("POST",))
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
@exige_permission("valider_piece")
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


@login_required
@exige_permission("editer_declarations", methodes=("POST",))
def aib_list(request):
    form = DeclarationAIBForm(request.POST or None)
    decl = None
    if request.method == "POST" and form.is_valid():
        decl = creer_declaration_aib(
            form.cleaned_data["configuration"], form.cleaned_data["annee"],
            form.cleaned_data["periode_num"], form.cleaned_data["base_imposable"], request.user,
        )
    return render(request, "fiscal/declaration_aib.html", {
        "form": form, "declaration": decl,
        "declarations": DeclarationAIB.objects.select_related("configuration")[:50],
    })


@login_required
@exige_permission("valider_piece")
def aib_comptabiliser(request, pk):
    decl = get_object_or_404(DeclarationAIB, pk=pk)
    if decl.statut != "VALIDEE":
        comptabiliser_aib(decl, request.user)
    return redirect("fiscal:aib_list")


@login_required
def aib_bordereau(request, pk):
    decl = get_object_or_404(DeclarationAIB, pk=pk)
    pdf = generer_bordereau_aib_pdf(decl)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="aib_{decl.annee}_{decl.periode_num:02d}.pdf"'
    return resp
