from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeclarationPeriodeForm
from .models import DeclarationTVA
from .services import comptabiliser_liquidation, creer_declaration_tva, generer_bordereau_pdf


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
