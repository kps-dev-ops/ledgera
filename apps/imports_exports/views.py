from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ImportPiecesForm
from .models import ExportJob, ImportJob
from .tasks import (
    export_balance_excel,
    export_balance_pdf,
    export_bilan_pdf,
    export_cr_pdf,
    export_fec,
    export_grand_livre_excel,
    export_journal_excel,
    import_excel_pieces,
)

EXPORT_TASKS = {
    "BALANCE_XLSX": export_balance_excel,
    "GL_XLSX": export_grand_livre_excel,
    "JOURNAL_XLSX": export_journal_excel,
    "BALANCE_PDF": export_balance_pdf,
    "BILAN_PDF": export_bilan_pdf,
    "CR_PDF": export_cr_pdf,
    "FEC": export_fec,
}


def _schema_name():
    return connection.schema_name


@login_required
def export_create(request, type_export):
    """Crée un ExportJob et lance la tâche Celery correspondante."""
    if request.method != "POST":
        return HttpResponseForbidden("POST requis")
    if type_export not in EXPORT_TASKS:
        return HttpResponseForbidden(f"Type d'export inconnu : {type_export}")
    parametres = {k: v for k, v in request.POST.items() if k != "csrfmiddlewaretoken"}
    job = ExportJob.objects.create(
        type_export=type_export,
        parametres=parametres,
        cree_par=request.user,
    )
    EXPORT_TASKS[type_export].delay(job.pk, _schema_name())
    return redirect("imports_exports:export_detail", pk=job.pk)


@login_required
def export_list(request):
    jobs = ExportJob.objects.filter(cree_par=request.user)
    return render(request, "imports_exports/export_list.html", {"jobs": jobs})


@login_required
def export_detail(request, pk):
    job = get_object_or_404(ExportJob, pk=pk, cree_par=request.user)
    return render(request, "imports_exports/export_detail.html", {"job": job})


@login_required
def export_status(request, pk):
    """Endpoint HTMX polling pour suivi temps réel."""
    job = get_object_or_404(ExportJob, pk=pk, cree_par=request.user)
    return render(request, "imports_exports/_export_status.html", {"job": job})


# --- Imports ---

@login_required
def import_create(request):
    if request.method == "POST":
        form = ImportPiecesForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.cree_par = request.user
            job.save()
            import_excel_pieces.delay(job.pk, _schema_name())
            return redirect("imports_exports:import_detail", pk=job.pk)
    else:
        form = ImportPiecesForm()
    return render(request, "imports_exports/import_form.html", {"form": form})


@login_required
def import_list(request):
    jobs = ImportJob.objects.filter(cree_par=request.user)
    return render(request, "imports_exports/import_list.html", {"jobs": jobs})


@login_required
def import_detail(request, pk):
    job = get_object_or_404(ImportJob, pk=pk, cree_par=request.user)
    return render(request, "imports_exports/import_detail.html", {"job": job})


@login_required
def import_status(request, pk):
    job = get_object_or_404(ImportJob, pk=pk, cree_par=request.user)
    return render(request, "imports_exports/_import_status.html", {"job": job})


@login_required
def export_download(request, pk):
    job = get_object_or_404(ExportJob, pk=pk, cree_par=request.user)
    if job.statut != "TERMINE" or not job.fichier:
        return HttpResponseForbidden("Export non disponible")
    return FileResponse(job.fichier.open("rb"), as_attachment=True, filename=job.fichier.name.split("/")[-1])
