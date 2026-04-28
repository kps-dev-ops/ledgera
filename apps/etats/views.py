from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.comptabilite.models import CompteComptable, Exercice, Journal

from . import selectors
from .services.bilan import compute_bilan
from .services.compte_resultat import compute_compte_resultat


def _get_exercice(request) -> Exercice:
    code = request.GET.get("exercice")
    if code:
        return get_object_or_404(Exercice, code=code)
    ex = Exercice.objects.order_by("-date_debut").first()
    if not ex:
        raise Exercice.DoesNotExist("Aucun exercice n'existe — créer un exercice d'abord.")
    return ex


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@login_required
def balance_view(request):
    exercice = _get_exercice(request)
    date_debut = _parse_date(request.GET.get("date_debut"))
    date_fin = _parse_date(request.GET.get("date_fin"))
    classes = [int(c) for c in request.GET.getlist("classe") if c.isdigit()]
    lignes = list(selectors.balance(exercice, date_debut, date_fin, classes or None))
    total_d = sum((row["total_debit"] or 0) for row in lignes)
    total_c = sum((row["total_credit"] or 0) for row in lignes)
    return render(request, "etats/balance.html", {
        "exercice": exercice,
        "lignes": lignes,
        "total_debit": total_d,
        "total_credit": total_c,
        "equilibre": total_d == total_c,
        "exercices": Exercice.objects.all(),
        "classes_selectionnees": classes,
        "date_debut": date_debut,
        "date_fin": date_fin,
    })


@login_required
def grand_livre_view(request):
    exercice = _get_exercice(request)
    comptes = list(selectors.comptes_mouvementes(exercice))
    return render(request, "etats/grand_livre.html", {
        "exercice": exercice,
        "comptes": comptes,
        "exercices": Exercice.objects.all(),
    })


@login_required
def grand_livre_compte_view(request, numero):
    exercice = _get_exercice(request)
    compte = get_object_or_404(CompteComptable, numero=numero)
    date_debut = _parse_date(request.GET.get("date_debut"))
    date_fin = _parse_date(request.GET.get("date_fin"))
    lignes = selectors.grand_livre_compte(compte, exercice, date_debut, date_fin)
    return render(request, "etats/grand_livre_compte.html", {
        "exercice": exercice,
        "compte": compte,
        "lignes": lignes,
        "solde_final": lignes[-1]["solde"] if lignes else 0,
        "date_debut": date_debut,
        "date_fin": date_fin,
    })


@login_required
def journal_view(request):
    exercice = _get_exercice(request)
    code = request.GET.get("journal")
    journaux = Journal.objects.filter(actif=True)
    journal_obj = None
    pieces = []
    if code:
        journal_obj = get_object_or_404(Journal, code=code)
        date_debut = _parse_date(request.GET.get("date_debut"))
        date_fin = _parse_date(request.GET.get("date_fin"))
        pieces = list(selectors.journal(journal_obj, exercice, date_debut, date_fin))
    return render(request, "etats/journal.html", {
        "exercice": exercice,
        "journaux": journaux,
        "journal": journal_obj,
        "pieces": pieces,
        "exercices": Exercice.objects.all(),
    })


@login_required
def bilan_view(request):
    exercice = _get_exercice(request)
    data = compute_bilan(exercice)
    data["exercices"] = Exercice.objects.all()
    return render(request, "etats/syscohada/bilan.html", data)


@login_required
def compte_resultat_view(request):
    exercice = _get_exercice(request)
    data = compute_compte_resultat(exercice)
    data["exercices"] = Exercice.objects.all()
    return render(request, "etats/syscohada/compte_resultat.html", data)


@login_required
def balance_auxiliaire_view(request):
    exercice = _get_exercice(request)
    compte_id = request.GET.get("compte")
    comptes_collectifs = selectors.comptes_collectifs_avec_tiers(exercice)
    compte = None
    lignes = []
    if compte_id:
        compte = get_object_or_404(CompteComptable, pk=compte_id)
        lignes = list(selectors.balance_auxiliaire(compte, exercice))
    total_d = sum((row["total_debit"] or 0) for row in lignes)
    total_c = sum((row["total_credit"] or 0) for row in lignes)
    return render(request, "etats/balance_auxiliaire.html", {
        "exercice": exercice,
        "comptes_collectifs": comptes_collectifs,
        "compte": compte,
        "lignes": lignes,
        "total_debit": total_d,
        "total_credit": total_c,
    })
